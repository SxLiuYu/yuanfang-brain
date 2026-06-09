"""Pydantic models for API requests and responses."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WsMessageType(str, Enum):
    HELLO = "hello"
    TRANSCRIPT = "transcript"
    TTS_CHUNK = "tts_chunk"
    TTS_DONE = "tts_done"
    LLM_CHUNK = "llm_chunk"
    LLM_DONE = "llm_done"
    TOOL_CALL = "tool_call"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


class WsMessage(BaseModel):
    type: WsMessageType
    trace_id: str | None = None
    data: Any = None
    error: str | None = None


class WsAudioMessage(BaseModel):
    type: str = "audio"
    trace_id: str | None = None
    format: str = "pcm"  # pcm / mp3
    sample_rate: int = 16000
    channels: int = 1
    bits: int = 16
