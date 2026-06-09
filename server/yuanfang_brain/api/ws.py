"""WebSocket handler for audio streaming with ASR."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from yuanfang_brain.api.schema import WsMessage, WsMessageType
from yuanfang_brain.asr.factory import transcribe as asr_transcribe
from yuanfang_brain.config import get_config
from yuanfang_brain.vad import VAD

logger = logging.getLogger(__name__)

connections: set[WebSocket] = set()
_connection_lock = asyncio.Lock()


def create_router() -> APIRouter:
    router = APIRouter()
    cfg = get_config()
    vad = VAD(sample_rate=16000, aggressiveness=2)

    @router.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket):
        await websocket.accept()
        conn_id = str(uuid.uuid4())[:8]
        async with _connection_lock:
            connections.add(websocket)

        trace_id = str(uuid.uuid4())
        logger.info(f"[{conn_id}] WS connected, trace_id={trace_id}")

        audio_buffer = b""
        silence_frames = 0
        SPEECH_THRESHOLD_FRAMES = 15  # ~450ms of speech to trigger
        SILENCE_THRESHOLD_FRAMES = 30  # ~900ms silence to end utterance

        try:
            hello = WsMessage(
                type=WsMessageType.HELLO,
                trace_id=trace_id,
                data={"conn_id": conn_id, "server": "yuanfang-brain"},
            )
            await websocket.send_text(hello.model_dump_json())

            while True:
                data = await websocket.receive()

                if data["type"] == "websocket.disconnect":
                    break

                if data["type"] == "websocket.receive":
                    if "text" in data:
                        try:
                            msg = WsMessage.model_validate_json(data["text"])
                            await _handle_text_message(websocket, msg, conn_id, trace_id)
                        except Exception as e:
                            logger.error(f"[{conn_id}] bad JSON: {e}")
                            err = WsMessage(type=WsMessageType.ERROR, trace_id=trace_id, error=str(e))
                            await websocket.send_text(err.model_dump_json())
                    elif "bytes" in data:
                        audio_buffer += data["bytes"]

                        # VAD: check if current frame is speech
                        frame_size = vad.frame_size
                        if len(audio_buffer) >= frame_size:
                            frame = audio_buffer[-frame_size:]
                            is_speech = vad.is_speech(frame)

                            if is_speech:
                                silence_frames = 0
                            else:
                                silence_frames += 1

                            # Emit partial transcript if we have enough speech frames
                            if silence_frames < SPEECH_THRESHOLD_FRAMES:
                                # Still in active speech
                                pass
                            elif len(audio_buffer) > frame_size * 5:
                                # End of utterance detected — transcribe
                                audio_to_transcribe = audio_buffer[:-frame_size * min(silence_frames, frame_size)]
                                if len(audio_to_transcribe) > 0:
                                    text = await asr_transcribe(audio_to_transcribe, sample_rate=16000)
                                    if text:
                                        ack = WsMessage(
                                            type=WsMessageType.TRANSCRIPT,
                                            trace_id=trace_id,
                                            data={"text": text, "final": True},
                                        )
                                        try:
                                            await websocket.send_text(ack.model_dump_json())
                                        except Exception:
                                            pass
                                # Keep last few frames for overlap
                                audio_buffer = audio_buffer[-frame_size * 2:]
                                silence_frames = 0

        except WebSocketDisconnect:
            logger.info(f"[{conn_id}] WS disconnected")
        except Exception as e:
            logger.error(f"[{conn_id}] WS error: {e}")
        finally:
            async with _connection_lock:
                connections.discard(websocket)

    return router


async def _handle_text_message(ws: WebSocket, msg: WsMessage, conn_id: str, trace_id: str):
    logger.debug(f"[{conn_id}] received msg type={msg.type}")
    if msg.type == WsMessageType.PING:
        pong = WsMessage(type=WsMessageType.PONG, trace_id=msg.trace_id)
        await ws.send_text(pong.model_dump_json())
    elif msg.type == WsMessageType.ERROR:
        logger.warning(f"[{conn_id}] client error: {msg.error}")
