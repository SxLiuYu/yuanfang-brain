"""VAD (Voice Activity Detection) module using webrtcvad."""

from __future__ import annotations

import logging
from typing import Generator

logger = logging.getLogger(__name__)


class VAD:
    """WebRTC VAD wrapper for chunking audio into speech segments."""

    def __init__(self, sample_rate: int = 16000, aggressiveness: int = 2):
        try:
            import webrtcvad
            self._vad = webrtcvad.Vad(aggressiveness)
        except ImportError:
            logger.warning("webrtcvad not available, VAD disabled")
            self._vad = None
        self._sample_rate = sample_rate
        self._frame_size = int(sample_rate * 0.03)  # 30ms frames

    @property
    def frame_size(self) -> int:
        return self._frame_size

    def is_speech(self, audio: bytes) -> bool:
        """Return True if frame contains speech."""
        if self._vad is None:
            return True  # Pass through when not available
        try:
            return self._vad.is_speech(audio, self._sample_rate)
        except Exception:
            return False

    def chunk(self, audio: bytes) -> Generator[bytes, None, None]:
        """Yield speech chunks from audio stream."""
        for i in range(0, len(audio), self._frame_size):
            frame = audio[i : i + self._frame_size]
            if len(frame) < self._frame_size:
                break
            if self.is_speech(frame):
                yield frame
