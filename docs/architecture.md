# Protocol

## Connection

```
ws://<mac-ip>:7001/ws
```

## Message Format

All messages are JSON objects (text frames) or raw PCM binary (audio frames).

### Client → Server

**Audio frame** (binary): raw PCM 16kHz/16bit/mono
**Text frame** (JSON):
```json
{
  "type": "ping",
  "trace_id": "optional-trace-id"
}
```

### Server → Client

```json
{
  "type": "hello | transcript | llm_chunk | llm_done | tts_chunk | tts_done | pong | error",
  "trace_id": "uuid",
  "data": { ... },
  "error": "string (only on error type)"
}
```

## Flow

```
Client                Server                    HA/MiniMax/Claude
 │                      │                              │
 │── PCM audio frame ──►│                              │
 │                      │── whisper.cpp transcribe ────►│
 │                      │◄─ transcript text ────────────│
 │◄─ transcript JSON ───│                              │
 │                      │── Claude -p prompt ─────────►│
 │◄─ llm_chunk JSON ─────│◄─ stream delta ─────────────│
 │◄─ llm_done JSON ─────│                              │
 │                      │── MiniMax t2a_v2 synthesize ►│
 │◄─ tts_chunk (b64 mp3)│◄─ mp3 chunk stream ──────────│
 │◄─ tts_done JSON ──────│                              │
```

## trace_id

Every request carries a `trace_id` (UUID v4) for observability.
Logs and metrics are indexed by trace_id for request-level tracing.

## Audio Format

- Sample rate: 16000 Hz
- Bit depth: 16-bit signed integer
- Channels: 1 (mono)
- Encoding: PCM linear (little-endian)

## VAD (Voice Activity Detection)

Uses webrtcvad with aggressiveness=2, 30ms frames.
Utterance end detected after ~600ms of silence.

## End-to-end Latency Targets

| Step | Target |
|---|---|
| VAD detection | < 50ms |
| ASR (local whisper.cpp) | < 150ms/utterance |
| LLM first token | < 800ms |
| TTS first audio chunk | < 1000ms |
| **Total E2E** | **< 1500ms** |
