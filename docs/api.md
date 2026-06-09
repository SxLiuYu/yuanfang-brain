# API Reference

## HTTP Endpoints

### `GET /health`
Returns server health status.

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "timestamp": "2026-06-09T12:00:00Z"
}
```

### `GET /version`
Returns version string.

**Response:**
```json
{
  "version": "0.1.0"
}
```

### `GET /metrics`
Prometheus-style metrics.

**Response:**
```json
{
  "requests_total": 0,
  "requests_active": 0,
  "transcriptions_total": 0,
  "tts_tokens_total": 0,
  "llm_tokens_total": 0,
  "ha_calls_total": 0,
  "uptime_seconds": 0
}
```

## WebSocket

### `WS /ws`

#### On Connect
Server immediately sends:
```json
{
  "type": "hello",
  "trace_id": "uuid",
  "data": {
    "conn_id": "8-char-id",
    "server": "yuanfang-brain"
  }
}
```

#### On Binary Audio
Client sends raw PCM frames. Server responds when silence is detected:

```json
{
  "type": "transcript",
  "trace_id": "uuid",
  "data": {
    "text": "打开客厅灯",
    "final": true
  }
}
```

#### LLM Streaming

```json
{"type": "llm_chunk", "trace_id": "uuid", "data": {"text": "已"}}
{"type": "llm_chunk", "trace_id": "uuid", "data": {"text": "打开"}}
{"type": "llm_chunk", "trace_id": "uuid", "data": {"text": "客厅灯"}}
{"type": "llm_done", "trace_id": "uuid", "data": {}}
```

#### TTS Streaming

```json
{"type": "tts_chunk", "trace_id": "uuid", "data": {"audio": "<base64 mp3>"}}
{"type": "tts_done", "trace_id": "uuid", "data": {}}
```

#### Ping/Pong

```json
{"type": "ping", "trace_id": "uuid"}
{"type": "pong", "trace_id": "uuid"}
```

## HA Tools (LLM function-calling)

Available to Claude when processing conversation context:

| Tool | Description |
|---|---|
| `ha_list_entities(domain?)` | List all HA entities, optionally filtered |
| `ha_get_state(entity_id)` | Get current state of a single entity |
| `ha_toggle(entity_id)` | Toggle a light/switch on/off |
| `ha_call_service(domain, service, entity_id?, data?)` | Call any HA service directly |
