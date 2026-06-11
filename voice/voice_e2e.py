"""End-to-end voice orchestrator: wav -> text -> intent -> (HA) -> TTS mp3.

Pipeline:
  1. transcribe wav to Chinese text
  2. parse_intent -> structured intent dict
  3. if action == "ha_service", call HA service and capture result
  4. build a response string from intent["response"] (or HA result)
  5. tts_speak response -> mp3 bytes
  6. return {text, audio (base64), ha_called}
"""
import base64
from typing import Any

from voice import intent
from voice.asr_transcribe import transcribe
from voice.tts_speak import tts_speak
from ha import assistant as ha


def voice_query(wav_path: str) -> dict[str, Any]:
    """Run the full voice pipeline against a wav file and return a result dict."""
    text = transcribe(wav_path)
    parsed = intent.parse_intent(text)
    ha_called = False
    response_text = parsed.get("response") or text
    if parsed.get("action") == "ha_service":
        service = parsed.get("service", "")
        entity_id = parsed.get("entity_id", "")
        kwargs = parsed.get("kwargs", {}) or {}
        domain, _, svc = service.partition(".")
        ok = ha.call_service(domain, svc, entity_id=entity_id, **kwargs)
        ha_called = bool(ok)
        if not ok:
            response_text = "抱歉,服务调用失败"
    mp3 = tts_speak(response_text)
    return {
        "text": response_text,
        "audio": base64.b64encode(mp3).decode("ascii"),
        "ha_called": ha_called,
    }
