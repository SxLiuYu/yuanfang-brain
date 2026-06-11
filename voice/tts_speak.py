"""MiniMax TTS via /t2a_v2 endpoint.

Returns raw mp3 bytes for the synthesized text.
"""
import base64
import os

import requests

_KEY_FILE = os.path.expanduser("~/.hermes/.secrets/minimax_cn.b64")
_BASE = os.environ.get("LAOPODADA_TTS_BASE", "https://api.minimaxi.com/v1")
_RETRIES = 2


def _get_key():
    with open(_KEY_FILE) as f:
        return base64.b64decode(f.read().strip()).decode("utf-8")


def tts_speak(text: str, voice: str = "female-shaonv") -> bytes:
    key = _get_key()
    payload = {
        "model": "speech-01-turbo",
        "text": text,
        "voice_setting": {"voice_id": voice, "speed": 1.0, "vol": 1.0, "pitch": 0},
        "audio_setting": {"sample_rate": 32000, "format": "mp3"},
    }
    last_err = None
    for _ in range(_RETRIES + 1):
        try:
            r = requests.post(
                f"{_BASE.rstrip('/')}/t2a_v2",
                json=payload,
                headers={"Authorization": f"Bearer {key}"},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            audio_b64 = data["data"]["audio"]
            return base64.b64decode(audio_b64)
        except Exception as e:
            last_err = e
    raise RuntimeError(f"TTS failed after {_RETRIES + 1} attempts: {last_err}")
