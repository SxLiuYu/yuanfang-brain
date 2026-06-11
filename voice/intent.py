"""LLM-based intent parser for home assistant commands.

Calls an Ollama/OMLX-compatible chat completions endpoint and asks the model
to return a strict JSON object describing the user's request.
"""
import json
import os
import re
from typing import Any

import requests

_LLM_URL = os.environ.get("OMLX_URL", "http://localhost:8081/v1") + "/chat/completions"
_LLM_MODEL = os.environ.get("INTENT_MODEL", "Qwen3.5-4B-MLX-4bit")
_CLOUD_URL = os.environ.get("CLOUD_LLM_URL", "https://api.minimaxi.com/v1/chat/completions")
_CLOUD_MODEL = os.environ.get("CLOUD_LLM_MODEL", "MiniMax-M3")
_CLOUD_KEY_FILE = os.path.expanduser(os.environ.get(
    "CLOUD_LLM_KEY_FILE", "~/.hermes/.secrets/minimax_cn.b64"
))
_LOCAL_TIMEOUT = 60.0  # OMLX thinking 模式 7-20s 推理需更长超时
_CLOUD_TIMEOUT = 15.0

_SYSTEM = (
    "你是一个家庭助手意图解析器。立即用 JSON 回复,不要思考、不要解释、不要 markdown。\n"
    "直接输出 JSON 对象,第一个字符必须是 `{`。\n"
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
    # Strip <think>...</think> blocks (MiniMax-M3 + OMLX Qwen3.5 wrap reasoning in them)
    text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL).strip()
    # Also strip "Thinking Process:\n..." pseudo-think blocks OMLX uses
    text = re.sub(r"Thinking Process:.*?(?=\{)", "", text, flags=re.DOTALL).strip()
    fenced = re.search(r"```json\s*(\{.*?})\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            return None
    # Last-resort: find first balanced { ... } in the text
    brace = re.search(r"\{.*}", text, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _call_local(text: str) -> str | None:
    """Try local LLM. Return raw content, or None on failure/timeout."""
    payload = {
        "model": _LLM_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": text},
        ],
        "temperature": 0.1,
        "max_tokens": 300,
        "chat_template_kwargs": {"enable_thinking": False},  # OMLX 关 thinking
    }
    try:
        resp = requests.post(_LLM_URL, json=payload, timeout=_LOCAL_TIMEOUT)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def _call_cloud(text: str) -> str | None:
    """Try cloud LLM fallback. Return raw content, or None on failure."""
    try:
        with open(_CLOUD_KEY_FILE) as f:
            import base64
            api_key = base64.b64decode(f.read().strip()).decode("utf-8")
    except Exception:
        return None
    payload = {
        "model": _CLOUD_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": text},
        ],
        "temperature": 0.1,
    }
    try:
        resp = requests.post(
            _CLOUD_URL,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=_CLOUD_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def parse_intent(text: str) -> dict[str, Any]:
    """Parse natural-language user text into a structured intent dict.

    Tries local LLM first (4s timeout), falls back to cloud LLM.
    """
    content = _call_local(text)
    provider = "local" if content else None
    if not content:
        content = _call_cloud(text)
        provider = "cloud" if content else None
    if not content:
        return dict(_FALLBACK)
    parsed = _extract_json(content)
    if not isinstance(parsed, dict) or "action" not in parsed:
        return dict(_FALLBACK)
    parsed.setdefault("response", "")
    parsed["_provider"] = provider or "none"
    return parsed
