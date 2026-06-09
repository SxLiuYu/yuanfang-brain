"""WebSocket handler for audio streaming."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from yuanfang_brain.api.schema import WsMessage, WsMessageType

logger = logging.getLogger(__name__)

# Global connection registry for broadcast / metrics
connections: set[WebSocket] = set()
_connection_lock = asyncio.Lock()


def create_router() -> APIRouter:
    router = APIRouter()

    @router.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket):
        await websocket.accept()
        conn_id = str(uuid.uuid4())[:8]
        async with _connection_lock:
            connections.add(websocket)

        trace_id = str(uuid.uuid4())
        logger.info(f"[{conn_id}] WS connected, trace_id={trace_id}")

        try:
            # Send hello
            hello = WsMessage(
                type=WsMessageType.HELLO,
                trace_id=trace_id,
                data={"conn_id": conn_id, "server": "yuanfang-brain"},
            )
            await websocket.send_text(hello.model_dump_json())

            while True:
                # Receive messages; handle both text (JSON) and binary (audio)
                try:
                    data = await websocket.receive()
                except Exception:
                    break

                if data["type"] == "websocket.disconnect":
                    break

                if data["type"] == "websocket.receive":
                    # Text JSON control message
                    if "text" in data:
                        try:
                            msg = WsMessage.model_validate_json(data["text"])
                            await _handle_text_message(websocket, msg, conn_id)
                        except Exception as e:
                            logger.error(f"[{conn_id}] bad JSON: {e}")
                            err = WsMessage(
                                type=WsMessageType.ERROR,
                                trace_id=trace_id,
                                error=str(e),
                            )
                            await websocket.send_text(err.model_dump_json())
                    # Binary audio — handled via receive_bytes
                    elif "bytes" in data:
                        await _handle_binary_audio(websocket, data["bytes"], conn_id, trace_id)

        except WebSocketDisconnect:
            logger.info(f"[{conn_id}] WS disconnected")
        except Exception as e:
            logger.error(f"[{conn_id}] WS error: {e}")
        finally:
            async with _connection_lock:
                connections.discard(websocket)

    return router


async def _handle_text_message(ws: WebSocket, msg: WsMessage, conn_id: str):
    """Handle incoming JSON control messages."""
    logger.debug(f"[{conn_id}] received msg type={msg.type}")

    if msg.type == WsMessageType.PING:
        pong = WsMessage(type=WsMessageType.PONG, trace_id=msg.trace_id)
        await ws.send_text(pong.model_dump_json())
    elif msg.type == WsMessageType.ERROR:
        logger.warning(f"[{conn_id}] client error: {msg.error}")

    # Future: transcript requests, tool responses, etc.
    ack = WsMessage(
        type=WsMessageType.TRANSCRIPT,
        trace_id=msg.trace_id,
        data={"status": "received"},
    )
    await ws.send_text(ack.model_dump_json())


async def _handle_binary_audio(ws: WebSocket, audio: bytes, conn_id: str, trace_id: str):
    """Handle incoming binary audio frames."""
    # Audio frames are passed to the ASR module for processing.
    # For now just echo back a placeholder transcript.
    logger.debug(f"[{conn_id}] received {len(audio)} bytes of audio, trace_id={trace_id}")
    # Placeholder — real implementation in Commit 2/3
    ack = WsMessage(
        type=WsMessageType.TRANSCRIPT,
        trace_id=trace_id,
        data={"text": "[audio received]", "final": True},
    )
    try:
        await ws.send_text(ack.model_dump_json())
    except Exception:
        pass
