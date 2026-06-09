"""ASR factory — local whisper.cpp with MiniMax fallback."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Try local first, fall back to MiniMax
_local_asr = None
_minimax_asr = None


def get_local_asr(model_name: str = "tiny"):
    global _local_asr
    if _local_asr is None:
        try:
            _local_asr = __import__("yuanfang_brain.asr.local", fromlist=["LocalASR"]).LocalASR(model_name)
            logger.info("Local ASR (whisper.cpp) available")
        except Exception as e:
            logger.warning(f"Local ASR unavailable: {e}")
            _local_asr = None
    return _local_asr


def get_minimax_asr():
    global _minimax_asr
    if _minimax_asr is None:
        _minimax_asr = __import__("yuanfang_brain.asr.minimax", fromlist=["MiniMaxASR"]).MiniMaxASR()
        logger.info("MiniMax ASR available")
    return _minimax_asr


async def transcribe(audio_pcm: bytes, sample_rate: int = 16000) -> str:
    """Transcribe with local-first, MiniMax fallback."""
    local = get_local_asr()
    if local is not None:
        try:
            return await local.transcribe(audio_pcm, sample_rate)
        except Exception as e:
            logger.warning(f"Local ASR failed: {e}, trying MiniMax")

    minimax = get_minimax_asr()
    if minimax:
        return await minimax.transcribe(audio_pcm, sample_rate)

    return ""
