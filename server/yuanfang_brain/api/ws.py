"""WebSocket handler: full ASR→LLM→TTS pipeline."""

from __future__ import annotations

import asyncio
import base64
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from yuanfang_brain.api.schema import WsMessage, WsMessageType
from yuanfang_brain.asr.factory import transcribe as asr_transcribe
from yuanfang_brain.conversation.manager import get_conversation_manager
from yuanfang_brain.config import get_config
from yuanfang_brain.ha.tools import register_ha_tools
from yuanfang_brain.llm.factory import get_llm
from yuanfang_brain.tts.factory import get_tts
from yuanfang_brain.vad import VAD

logger = logging.getLogger(__name__)

connections: set[WebSocket] = set()
_connection_lock = asyncio.Lock()


def create_router() -> APIRouter:
    router = APIRouter()
    cfg = get_config()
    vad = VAD(sample_rate=16000, aggressiveness=2)
    ha_tools = register_ha_tools()

    @router.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket):
        await websocket.accept()
        conn_id = str(uuid.uuid4())[:8]
        async with _connection_lock:
            connections.add(websocket)

        trace_id = str(uuid.uuid4())
        manager = get_conversation_manager()
        logger.info(f"[{conn_id}] WS connected, trace_id={trace_id}")

        audio_buffer = b""
        silence_frames = 0
        SPEECH_THRESHOLD = 10   # ~300ms
        SILENCE_THRESHOLD = 20  # ~600ms silence → end utterance

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
                            await _handle_text_message(websocket, msg, conn_id, trace_id, manager, ha_tools)
                        except Exception as e:
                            logger.error(f"[{conn_id}] bad JSON: {e}")
                            err = WsMessage(type=WsMessageType.ERROR, trace_id=trace_id, error=str(e))
                            await websocket.send_text(err.model_dump_json())
                    elif "bytes" in data:
                        audio_buffer += data["bytes"]
                        frame_size = vad.frame_size

                        if len(audio_buffer) >= frame_size:
                            frame = audio_buffer[-frame_size:]
                            is_speech = vad.is_speech(frame)

                            if is_speech:
                                silence_frames = 0
                            else:
                                silence_frames += 1

                            # End of utterance: silence threshold reached
                            if silence_frames >= SILENCE_THRESHOLD and len(audio_buffer) > frame_size * 5:
                                audio_to_transcribe = audio_buffer[:-frame_size * min(silence_frames, SILENCE_THRESHOLD)]
                                audio_buffer = audio_buffer[-frame_size * 2:]

                                if len(audio_to_transcribe) > 0:
                                    text = await asr_transcribe(audio_to_transcribe, sample_rate=16000)
                                    if text:
                                        # Send transcript
                                        ack = WsMessage(
                                            type=WsMessageType.TRANSCRIPT,
                                            trace_id=trace_id,
                                            data={"text": text, "final": True},
                                        )
                                        await websocket.send_text(ack.model_dump_json())

                                        # Add to conversation history
                                        manager.add_user_message(conn_id, text)

                                        # Stream LLM response
                                        llm = get_llm()
                                        if llm:
                                            async for llm_obj in llm.complete_stream(text, conn_id):
                                                if llm_obj.get("type") == "content_block_delta":
                                                    delta = llm_obj.get("delta", {})
                                                    text_chunk = delta.get("text", "") if isinstance(delta, dict) else str(delta)
                                                    if text_chunk:
                                                        chunk_msg = WsMessage(
                                                            type=WsMessageType.LLM_CHUNK,
                                                            trace_id=trace_id,
                                                            data={"text": text_chunk},
                                                        )
                                                        try:
                                                            await websocket.send_text(chunk_msg.model_dump_json())
                                                        except Exception:
                                                            pass
                                                elif llm_obj.get("type") == "content_block_stop":
                                                    done_msg = WsMessage(
                                                        type=WsMessageType.LLM_DONE,
                                                        trace_id=trace_id,
                                                        data={},
                                                    )
                                                    try:
                                                        await websocket.send_text(done_msg.model_dump_json())
                                                    except Exception:
                                                        pass

                                        # TTS: synthesize full response text
                                        tts = get_tts()
                                        if tts and text:
                                            try:
                                                async for mp3_chunk in tts.synthesize_stream(text):
                                                    tts_msg = WsMessage(
                                                        type=WsMessageType.TTS_CHUNK,
                                                        trace_id=trace_id,
                                                        data={"audio": base64.b64encode(mp3_chunk).decode()},
                                                    )
                                                    try:
                                                        await websocket.send_text(tts_msg.model_dump_json())
                                                    except Exception:
                                                        pass
                                                done_tts = WsMessage(
                                                    type=WsMessageType.TTS_DONE,
                                                    trace_id=trace_id,
                                                    data={},
                                                )
                                                await websocket.send_text(done_tts.model_dump_json())
                                            except Exception as e:
                                                logger.error(f"[{conn_id}] TTS error: {e}")

                                silence_frames = 0

        except WebSocketDisconnect:
            logger.info(f"[{conn_id}] WS disconnected")
        except Exception as e:
            logger.error(f"[{conn_id}] WS error: {e}")
        finally:
            async with _connection_lock:
                connections.discard(websocket)

    return router


async def _handle_text_message(
    ws: WebSocket, msg: WsMessage, conn_id: str, trace_id: str, manager, ha_tools
):
    logger.debug(f"[{conn_id}] received msg type={msg.type}")
    if msg.type == WsMessageType.PING:
        pong = WsMessage(type=WsMessageType.PONG, trace_id=msg.trace_id)
        await ws.send_text(pong.model_dump_json())
    elif msg.type == WsMessageType.ERROR:
        logger.warning(f"[{conn_id}] client error: {msg.error}")
