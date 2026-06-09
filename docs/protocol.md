# yuanfang-brain WebSocket Protocol

## Connection

```
ws://<mac-ip>:7001/ws
```

## Transport

- **Audio**: raw binary PCM frames, 16000 Hz / 16-bit / mono / little-endian
- **Control**: JSON text frames

## Connection Flow

1. Client connects → Server sends `hello` immediately
2. Client sends binary PCM frames (no framing needed — just raw samples)
3. Server detects silence via VAD, runs ASR, responds with `transcript`
4. Server streams `llm_chunk` → `llm_done` → `tts_chunk` → `tts_done`

## Message Types

### Server → Client

| type | direction | description |
|---|---|---|
| `hello` | server→client | Sent on connect |
| `transcript` | server→client | ASR result |
| `llm_chunk` | server→client | LLM text token |
| `llm_done` | server→client | LLM stream complete |
| `tts_chunk` | server→client | TTS mp3 chunk (base64) |
| `tts_done` | server→client | TTS audio complete |
| `pong` | server→client | Response to ping |
| `error` | server→client | Error message |

### Client → Server

| type | direction | description |
|---|---|---|
| *(binary PCM)* | client→server | Raw audio |
| `ping` | client→server | Liveness check |

## Example Session

```
Client                      Server                       HA
  │                           │                          │
  │────── binary PCM ─────────►│                          │
  │                           │── whisper.cpp ──────────►│
  │                           │◄─ "打开客厅灯" ───────────│
  │◄──── transcript ──────────│                          │
  │                           │── ha_toggle ─────────────►│
  │                           │◄─ OK ─────────────────────│
  │                           │── Claude -p ────────────►│
  │◄──── llm_chunk ───────────│◄─ "已打开客厅灯" ──────────│
  │◄──── llm_done ────────────│                          │
  │                           │── MiniMax t2a_v2 ────────►│
  │◄──── tts_chunk (b64) ─────│◄─ mp3 stream ──────────────│
  │◄──── tts_done ────────────│                          │
```

## trace_id

Every message carries a `trace_id` UUID for observability.
Logs are greppable by trace_id.

## Audio Format

- Sample rate: 16000 Hz
- Bit depth: 16-bit signed integer
- Channels: 1 (mono)
- Byte order: little-endian
- No header — raw PCM
