"""MiniMax ASR fallback when local whisper is unavailable or for better Chinese accuracy."""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import AsyncGenerator

import httpx

from yuanfang_brain.config import get_config

logger = logging.getLogger(__name__)


class MiniMaxASR:
    """MiniMax ASR API (embo-01) fallback for Chinese and cloud fallback."""

    def __init__(self):
        cfg = get_config()
        self.api_key = cfg.minimax.api_key
        self.group_id = cfg.minimax.group_id
        self.base_url = "https://api.minimax.io/v1"

    async def transcribe(self, audio_pcm: bytes, sample_rate: int = 16000) -> str:
        """Transcribe PCM audio via MiniMax ASR API."""
        if not self.api_key:
            logger.warning("MiniMax API key not configured, skipping ASR")
            return ""

        # Convert PCM to WAV base64 for MiniMax
        import io
        import wave

        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_pcm)
        wav_b64 = base64.b64encode(wav_io.getvalue()).decode()

        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": "embo-01",
            "audio_file": wav_b64,
            "language_boost": "zh",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/asr",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("text", "")

    async def transcribe_stream(
        self, audio_chunks: AsyncGenerator[bytes, None], sample_rate: int = 16000
    ) -> AsyncGenerator[str, None]:
        """Stream transcription via MiniMax (chunk-by-chunk)."""
        buffer = b""
        async for chunk in audio_chunks:
            buffer += chunk
            if len(buffer) >= sample_rate * 5:  # Min 5 seconds per chunk
                text = await self.transcribe(buffer, sample_rate)
                if text:
                    yield text
                buffer = b""
        if buffer:
            text = await self.transcribe(buffer, sample_rate)
            if text:
                yield text
