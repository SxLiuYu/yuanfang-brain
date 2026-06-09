"""MiniMax TTS streaming module (t2a_v2)."""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import AsyncGenerator

import httpx

from yuanfang_brain.config import get_config

logger = logging.getLogger(__name__)


class MiniMaxTTS:
    """MiniMax text-to-audio streaming via t2a_v2 API."""

    def __init__(self):
        cfg = get_config()
        self.api_key = cfg.minimax.api_key
        self.group_id = cfg.minimax.group_id
        self.base_url = "https://api.minimax.io/v1"

    async def synthesize_stream(
        self, text: str, voice: str = "male-qn_qingse"
    ) -> AsyncGenerator[bytes, None]:
        """Synthesize text to mp3 audio stream, yielding chunks as they arrive."""
        if not self.api_key:
            logger.warning("MiniMax API key not configured, TTS disabled")
            return

        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": "speech-01",
            "text": text,
            "stream": True,
            "voice_settings": {
                "voice_id": voice,
                "speed": 1.0,
                "pitch": 0,
                "volume": 0,
            },
        }

        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/t2a_v2",
                headers=headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes(chunk_size=4096):
                    if chunk:
                        yield chunk

    async def synthesize(self, text: str, voice: str = "male-qn_qingse") -> bytes:
        """Synthesize text and return full audio bytes."""
        chunks = []
        async for chunk in self.synthesize_stream(text, voice):
            chunks.append(chunk)
        return b"".join(chunks)
