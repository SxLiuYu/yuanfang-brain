"""Wake-word detection using openWakeWord."""
from __future__ import annotations

import logging
import os
from typing import NamedTuple

import numpy as np

logger = logging.getLogger(__name__)

# Lazy-loaded importer
_oww_model = None
_oww_decoder = None


class WakeResult(NamedTuple):
    detected: bool
    model: str
    score: float


def _get_decoder():
    global _oww_decoder
    if _oww_decoder is None:
        try:
            import numpy as np
            from openwakeword.model import Model

            # Download/prepare models on first use if not present
            model_path = os.path.join(
                os.path.expanduser("~/.cache/openwakeword"),
                "alexa.onnx",
            )
            if not os.path.exists(model_path):
                logger.info("openWakeWord model not found, downloading alexa model...")
            else:
                logger.info(f"openWakeWord model found at {model_path}")

            _oww_decoder = Model(
                model_path=model_path if os.path.exists(model_path) else "alexa",
                inference_framework="onnx",
            )
            logger.info("openWakeWord decoder initialised")
        except Exception as e:
            logger.warning(f"Could not initialise openWakeWord: {e}")
            _oww_decoder = None
    return _oww_decoder


def _parse_wav(path: str) -> np.ndarray:
    """Parse a 16 kHz mono WAV file and return float32 samples."""
    import struct

    with open(path, "rb") as f:
        riff = f.read(4)
        if riff != b"RIFF":
            raise ValueError(f"Not a valid WAV file: {path}")
        f.read(4)  # file size
        wave = f.read(4)
        if wave != b"WAVE":
            raise ValueError(f"Not a valid WAV file: {path}")

        # Find fmt chunk
        while True:
            chunk_id = f.read(4)
            if not chunk_id:
                raise ValueError("WAV file missing fmt chunk")
            chunk_size = struct.unpack("<I", f.read(4))[0]
            if chunk_id == b"fmt ":
                f.read(chunk_size)  # fmt data (we only need data chunk)
                break
            else:
                f.read(chunk_size)

        # Find data chunk
        while True:
            chunk_id = f.read(4)
            if not chunk_id:
                raise ValueError("WAV file missing data chunk")
            chunk_size = struct.unpack("<I", f.read(4))[0]
            if chunk_id == b"data":
                audio_data = f.read(chunk_size)
                break
            else:
                f.read(chunk_size)

    return np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0


def check_wake_word(wav_path: str) -> WakeResult:
    """Run wake-word detection on a 16 kHz mono WAV file.

    Returns WakeResult(detected=True, model, score) if a wake word is detected,
    otherwise WakeResult(detected=False, model, 0.0).
    """
    # Always validate WAV structure first (raises ValueError on bad file)
    samples = _parse_wav(wav_path)

    decoder = _get_decoder()
    if decoder is None:
        return WakeResult(detected=False, model="alexa", score=0.0)

    # openWakeWord expects 16 kHz audio; chunk into 80 ms frames (1280 samples)
    frame_size = 1280
    scores = []
    model_names = list(decoder.models.keys())
    if not model_names:
        model_names = ["alexa"]

    for i in range(0, len(samples) - frame_size, frame_size):
        frame = samples[i : i + frame_size]
        try:
            preds = decoder.predict(frame)
            for m in model_names:
                s = preds.get(m, {}).get("scores", [0.0])[0]
                scores.append((m, s))
        except Exception:
            pass

    if not scores:
        return WakeResult(detected=False, model="alexa", score=0.0)

    best_model, best_score = max(scores, key=lambda x: x[1])
    detected = best_score > 0.5

    logger.info(f"detect_from_wav({wav_path}): detected={detected}, model={best_model}, score={best_score:.4f}")
    return WakeResult(detected=detected, model=best_model, score=float(best_score))


def get_decoder():
    """Return the shared openWakeWord decoder instance (lazy init)."""
    return _get_decoder()