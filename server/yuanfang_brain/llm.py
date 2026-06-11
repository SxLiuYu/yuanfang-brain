"""LLM chat: local OMLX first, cloud MiniMax fallback on connection failure."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

import httpx

LOCAL_URL = "http://localhost:8080/v1/chat/completions"
LOCAL_MODEL = "mlx-community/Qwen3-4B-4bit"
CLOUD_URL = "https://api.minimaxi.com/v1/chat/completions"
CLOUD_MODEL = "MiniMax-M3"
CLOUD_KEY_FILE = "~/.hermes/.secrets/minimax_cn.b64"


def _cloud_key() -> str:
    p = Path(os.path.expanduser(CLOUD_KEY_FILE))
    if not p.exists():
        return ""
    try:
        return base64.b64decode(p.read_bytes()).decode().strip()
    except Exception:
        return ""


def _post(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    r = httpx.post(url, json=payload, headers=headers, timeout=60.0)
    r.raise_for_status()
    return r.json()


def _call_omlx(messages: list[dict], model: str) -> dict[str, Any]:
    data = _post(
        LOCAL_URL,
        {"model": model or LOCAL_MODEL, "messages": messages, "stream": False},
        {"Content-Type": "application/json"},
    )
    return {
        "provider": "omlx",
        "model": data.get("model", model or LOCAL_MODEL),
        "content": data["choices"][0]["message"]["content"],
    }


def _call_cloud(messages: list[dict], model: str) -> dict[str, Any]:
    key = _cloud_key()
    if not key:
        raise RuntimeError("cloud key missing")
    data = _post(
        CLOUD_URL,
        {"model": model or CLOUD_MODEL, "messages": messages, "stream": False},
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    return {
        "provider": "minimax",
        "model": data.get("model", model or CLOUD_MODEL),
        "content": data["choices"][0]["message"]["content"],
    }


def chat(messages: list[dict], model: str | None = None) -> dict[str, Any]:
    """Try local OMLX; on ConnectError, fall through to MiniMax cloud."""
    try:
        return _call_omlx(messages, model or LOCAL_MODEL)
    except (httpx.ConnectError, httpx.RequestError):
        return _call_cloud(messages, model or CLOUD_MODEL)
