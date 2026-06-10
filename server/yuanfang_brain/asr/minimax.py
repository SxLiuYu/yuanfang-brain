"""MiniMax ASR via Coding Plan (sk-cp) — OpenAI-compatible /audio/transcriptions.

No group_id required for Coding Plan subscriptions.
"""

from __future__ import annotations

import asyncio
import io
import logging
import wave
from typing import AsyncGenerator

import httpx

from yuanfang_brain.config import get_config

logger = logging.getLogger(__name__)


class MiniMaxASR:
    """MiniMax ASR via Coding Plan (sk-cp) — OpenAI-compatible."""

    def __init__(self):
        cfg = get_config()
        self.api_key = cfg.minimax.resolved_key()
        self.base_url = (
            getattr(cfg.minimax, "base", "") or "https://api.minimaxi.com/v1"
        ).rstrip("/")
        self.model = getattr(cfg.minimax, "asr_model", "whisper-1") or "whisper-1"

    @staticmethod
    def _pcm_to_wav(pcm: bytes, sample_rate: int = 16000) -> bytes:
        """Wrap raw PCM (16-bit mono) into a WAV container."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm)
        return buf.getvalue()

    async def transcribe(self, audio_pcm: bytes, sample_rate: int = 16000) -> str:
        """Transcribe raw 16-bit mono PCM via Coding Plan /audio/transcriptions."""
        if not self.api_key:
            logger.warning("MiniMax API key not configured, skipping ASR")
            return ""

        wav_bytes = self._pcm_to_wav(audio_pcm, sample_rate)
        headers = {"Authorization": f"Bearer {self.api_key}"}
        # multipart/form-data: file + model (+ optional language)
        files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
        data = {"model": self.model, "language": "zh"}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
            )
            resp.raise_for_status()
            body = resp.json()
            return body.get("text", "")

    async def transcribe_stream(
        self, audio_chunks: AsyncGenerator[bytes, None], sample_rate: int = 16000
    ) -> AsyncGenerator[str, None]:
        """Stream transcription via MiniMax (chunk-by-chunk, ≥5s per call)."""
        buffer = b""
        async for chunk in audio_chunks:
            buffer += chunk
            if len(buffer) >= sample_rate * 5:  # Min 5 seconds
                text = await self.transcribe(buffer, sample_rate)
                if text:
                    yield text
                buffer = b""
        if buffer:
            text = await self.transcribe(buffer, sample_rate)
            if text:
                yield text
