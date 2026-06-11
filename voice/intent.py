"""LLM-based intent parser for home assistant commands.

Calls an Ollama/OMLX-compatible chat completions endpoint and asks the model
to return a strict JSON object describing the user's request.
"""
import json
import os
import re
from typing import Any

import requests

_LLM_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/v1") + "/chat/completions"
_LLM_MODEL = os.environ.get("INTENT_MODEL", "mlx-community/Qwen3-4B-4bit")

_SYSTEM = (
    "你是一个家庭助手意图解析器。始终用 JSON 回复,不要包含解释或 markdown。\n"
    "字段:\n"
    '  "action": "ha_service" | "query" | "chat"\n'
    '  "service": HA 服务名(例如 "light.turn_on"),仅当 action=ha_service 时需要\n'
    '  "entity_id": HA 实体 ID(例如 "light.living_room"),仅当 action=ha_service 时需要\n'
    '  "area": 房间名(中文),例如 "客厅"\n'
    '  "response": 用中文简短回复用户(1-20 字)\n'
    "示例: {\"action\":\"ha_service\",\"service\":\"light.turn_on\","
    "\"entity_id\":\"light.living_room\",\"area\":\"客厅\",\"response\":\"好的,已打开客厅灯\"}"
)

_FALLBACK: dict[str, Any] = {"action": "chat", "response": "我没听懂"}


def _extract_json(text: str) -> dict[str, Any] | None:
    fenced = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def parse_intent(text: str) -> dict[str, Any]:
    """Parse natural-language user text into a structured intent dict."""
    payload = {
        "model": _LLM_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": text},
        ],
        "temperature": 0.1,
    }
    try:
        resp = requests.post(_LLM_URL, json=payload, timeout=30)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return dict(_FALLBACK)
    parsed = _extract_json(content)
    if not isinstance(parsed, dict) or "action" not in parsed:
        return dict(_FALLBACK)
    parsed.setdefault("response", "")
    return parsed
