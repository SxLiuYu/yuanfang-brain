"""MiniMax ASR via OpenAI-compatible /audio/transcriptions endpoint.

Transcribes an audio file to Chinese text using the whisper-1 model.
"""
import base64
import os
from pathlib import Path

import requests

_BASE_URL = os.environ.get("LAOPODADA_ASR_BASE", "https://api.minimaxi.com/v1")
_API_KEY_FILE = Path.home() / ".hermes" / ".secrets" / "minimax_cn.b64"
_TIMEOUT = 30
_RETRIES = 2


def _api_key() -> str:
    return base64.b64decode(_API_KEY_FILE.read_text().strip()).decode("utf-8")


def transcribe(audio_path: str) -> str:
    """Transcribe `audio_path` to Chinese text via MiniMax ASR."""
    url = f"{_BASE_URL}/audio/transcriptions"
    headers = {"Authorization": f"Bearer {_api_key()}"}
    last_err: Exception | None = None
    for _ in range(_RETRIES + 1):
        try:
            with open(audio_path, "rb") as fh:
                files = {"file": (Path(audio_path).name, fh, "application/octet-stream")}
                data = {"model": "whisper-1"}
                resp = requests.post(
                    url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=_TIMEOUT,
                )
            resp.raise_for_status()
            return resp.json()["text"]
        except (requests.RequestException, KeyError, ValueError) as exc:
            last_err = exc
    raise RuntimeError(f"ASR failed after {_RETRIES + 1} attempts: {last_err}")
