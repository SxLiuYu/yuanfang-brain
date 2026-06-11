"""MiniMax (laopodada) TTS client.

Speaks text via an OpenAI-compatible /audio/speech endpoint and yields
mp3 bytes either as one blob or split on Chinese punctuation.
"""
import base64
import os
import re
import time
from pathlib import Path
from typing import Iterator

import requests

_BASE = os.environ.get("LAOPODADA_TTS_BASE", "https://api.minimaxi.com/v1")
_KEY_FILE = Path.home() / ".hermes" / ".secrets" / "minimax_cn.b64"
_TIMEOUT = 30
_RETRIES = 2


def _api_key() -> str:
    return base64.b64decode(_KEY_FILE.read_text().strip()).decode("utf-8")


def _synthesize(text: str, voice: str) -> bytes:
    url = f"{_BASE}/audio/speech"
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }
    body = {"model": "speech-01-turbo", "input": text, "voice": voice,
            "response_format": "mp3"}
    last_exc: Exception | None = None
    for attempt in range(_RETRIES + 1):
        try:
            resp = requests.post(url, json=body, headers=headers, timeout=_TIMEOUT)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < _RETRIES:
                time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"TTS failed after {_RETRIES + 1} attempts: {last_exc}")


def tts_speak(text: str, voice: str = "female-shaonv") -> bytes:
    """Synthesize `text` to an mp3 byte string."""
    return _synthesize(text, voice)


_SPLIT = re.compile(r"(?<=[。！？!?；;])")


def tts_stream_chunks(text: str, chunk_size: int = 20) -> Iterator[bytes]:
    """Stream mp3 chunks, splitting on Chinese sentence punctuation."""
    pieces = [p.strip() for p in _SPLIT.split(text) if p.strip()]
    if not pieces:
        pieces = [text]
    buf = ""
    for piece in pieces:
        buf += piece
        if len(buf) >= chunk_size:
            yield _synthesize(buf, "female-shaonv")
            buf = ""
    if buf:
        yield _synthesize(buf, "female-shaonv")
