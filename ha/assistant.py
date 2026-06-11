"""Minimal Home Assistant REST client.

Reads the long-lived token from ~/.yuanfang-brain/ha_token.b64 and
exposes list_entities / call_service against the HA REST API.
"""
import base64
import os
from pathlib import Path
from typing import Any

import requests

_HA_URL = os.environ.get("HA_URL", "http://192.168.1.10:8123").rstrip("/")
_TOKEN_FILE = Path.home() / ".yuanfang-brain" / "ha_token.b64"
_TIMEOUT = 10


def _token() -> str:
    return base64.b64decode(_TOKEN_FILE.read_text().strip()).decode("utf-8")


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
    }


def list_entities() -> list[dict[str, Any]]:
    """GET /api/states — return every entity currently exposed by HA."""
    resp = requests.get(f"{_HA_URL}/api/states", headers=_headers(), timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def call_service(domain: str, service: str, entity_id: str, **kwargs: Any) -> bool:
    """POST /api/services/{domain}/{service} — fire an HA service call."""
    payload: dict[str, Any] = {"entity_id": entity_id}
    payload.update(kwargs)
    url = f"{_HA_URL}/api/services/{domain}/{service}"
    resp = requests.post(url, headers=_headers(), json=payload, timeout=_TIMEOUT)
    return resp.ok
