"""MiniMax TTS streaming module — Coding Plan (sk-cp, OpenAI-compatible).

Uses POST {base}/audio/speech with the OpenAI TTS API shape.
No group_id required for Coding Plan subscriptions.
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncGenerator

import httpx

from yuanfang_brain.config import get_config

logger = logging.getLogger(__name__)


class MiniMaxTTS:
    """MiniMax text-to-audio via Coding Plan (sk-cp) — OpenAI-compatible."""

    def __init__(self):
        cfg = get_config()
        self.api_key = cfg.minimax.resolved_key()
        # Prefer yaml `base`, fall back to Coding Plan default
        self.base_url = (
            getattr(cfg.minimax, "base", "") or "https://api.minimaxi.com/v1"
        ).rstrip("/")
        self.model = getattr(cfg.minimax, "tts_model", "speech-01") or "speech-01"
        # Default voice (OpenAI-style; MiniMax may map or accept)
        self.default_voice = "alloy"

    async def synthesize_stream(
        self, text: str, voice: str | None = None
    ) -> AsyncGenerator[bytes, None]:
        """Synthesize text to mp3 audio stream, yielding chunks as they arrive."""
        if not self.api_key:
            logger.warning("MiniMax API key not configured, TTS disabled")
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": text,
            "voice": voice or self.default_voice,
            "response_format": "mp3",
        }

        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/audio/speech",
                headers=headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes(chunk_size=4096):
                    if chunk:
                        yield chunk

    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        """Synthesize text and return full audio bytes."""
        chunks = []
        async for chunk in self.synthesize_stream(text, voice):
            chunks.append(chunk)
        return b"".join(chunks)
