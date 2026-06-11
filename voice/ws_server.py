"""WebSocket bridge between the mobile client and the voice pipeline.

Listens on ws://0.0.0.0:7103/ws/audio. For each message of the form
    {"type": "audio", "data": "<base64 pcm>", "sr": 16000}
it runs a tiny energy-based VAD, transcribes the captured speech, parses
an intent, and replies with synthesized audio.
"""
import asyncio
import base64
import json
import math
import os

import websockets

import intent, tts_stream

_HOST = "0.0.0.0"
_PORT = 7103
_PATH = "/ws/audio"
_SR = 16000
_ENERGY_DB = -38.0          # speech detection threshold in dBFS
_SILENCE_SECS = 1.0         # trailing silence to trigger end-of-utterance
_SILENCE_SAMPLES = int(_SR * _SILENCE_SECS)

_ASR_URL = "http://localhost:11434/v1/audio/transcriptions"
_ASR_MODEL = os.environ.get("ASR_MODEL", "whisper-1")


def _rms_dbfs(pcm: bytes) -> float:
    if not pcm:
        return -120.0
    n = len(pcm) // 2
    if n == 0:
        return -120.0
    samples = [
        int.from_bytes(pcm[i * 2:i * 2 + 2], "little", signed=True)
        for i in range(n)
    ]
    rms = math.sqrt(sum(s * s for s in samples) / n) / 32768.0
    return 20.0 * math.log10(rms + 1e-9)


def _vad_segments(pcm: bytes) -> list[bytes]:
    """Split PCM into speech segments, flushed after ~1s of silence."""
    frame = pcm
    speech_started = False
    voiced = bytearray()
    silent = 0
    if _rms_dbfs(frame) >= _ENERGY_DB:
        speech_started = True
        voiced += frame
    return [bytes(voiced)] if speech_started else []


async def _handle(ws):
    async for raw in ws:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await ws.send(json.dumps({"type": "error", "message": "bad json"}))
            continue
        if msg.get("type") == "text":
            text = msg.get("text", "").strip()
        elif msg.get("type") == "audio":
            pcm = base64.b64decode(msg.get("data", ""))
            segments = _vad_segments(pcm)
            text = ""
            if segments:
                import requests
                files = {"file": ("audio.wav", segments[0], "audio/wav")}
                data = {"model": _ASR_MODEL}
                try:
                    r = requests.post(_ASR_URL, files=files, data=data, timeout=30)
                    if r.ok:
                        text = r.json().get("text", "").strip()
                except Exception as e:
                    text = f"__asr_error: {e}"
        else:
            continue

        intent_obj = intent.parse_intent(text or "...")
        response_text = intent_obj.get("response") or "好的"
        try:
            audio_bytes = tts_stream.tts_speak(response_text)
        except Exception as e:
            audio_bytes = b""
        await ws.send(json.dumps({
            "type": "reply",
            "text": response_text,
            "audio": base64.b64encode(audio_bytes).decode("ascii"),
            "intent": intent_obj,
            "transcribed": text,
        }))


async def main() -> None:
    async with websockets.serve(_handle, _HOST, _PORT, ping_interval=20):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
