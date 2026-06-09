"""TTS factory."""

from __future__ import annotations

import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

_tts: "MiniMaxTTS | None" = None


def get_tts():
    global _tts
    if _tts is None:
        try:
            _tts = __import__("yuanfang_brain.tts.minimax", fromlist=["MiniMaxTTS"]).MiniMaxTTS()
            logger.info("MiniMax TTS available")
        except Exception as e:
            logger.warning(f"TTS unavailable: {e}")
            _tts = None
    return _tts
