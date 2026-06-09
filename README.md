# yuanfang-brain

**Local-first voice + smart home fusion system** — voice control your Home Assistant home via a Mac daemon and mobile clients.

## Architecture

```
Clients (iOS/Android/Mac)                    yuanfang-brain-server (Mac)
┌─────────────────────┐                     ┌──────────────────────────────────┐
│  AVAudioEngine      │── PCM 16kHz ──────►│  WS :7001                        │
│  URLSessionWebSocket│◄── TTS mp3 ────────│  ├─ VAD (webrtcvad)               │
│  AVAudioPlayer      │                     │  ├─ ASR (whisper.cpp + MiniMax)   │
└─────────────────────┘                     │  ├─ LLM (Claude -p streaming)    │
                                             │  ├─ TTS (MiniMax t2a_v2)          │
                                             │  ├─ HA Bridge (REST API :8123)    │
                                             │  ├─ Conversation Manager         │
                                             │  └─ LanceDB Memory                │
                                             └──────────────────────────────────┘
                                                                                │
                                                    Home Assistant ────────────┘
                                                    (192.168.1.10:8123)
```

## Quick Start

### 1. Server

```bash
cd ~/repos/yuanfang-brain/server
./scripts/start.sh
# Edit ~/.yuanfang-brain/config.yaml with your HA token and MiniMax API key
```

### 2. iOS Client

```bash
cd ~/repos/yuanfang-brain/clients/ios/HermesVoice
xcodegen generate
xcodebuild -project HermesVoice.xcodeproj -target HermesVoice \
  -sdk iphoneos26.5 -arch arm64 CODE_SIGN_IDENTITY="-" CODE_SIGNING_REQUIRED=NO build
```

### 3. Android Client

```bash
cd ~/repos/yuanfang-brain/clients/android
./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk
```

## Project Structure

```
yuanfang-brain/
├── server/                     Python daemon (FastAPI + uvicorn)
│   ├── yuanfang_brain/
│   │   ├── api/                 HTTP + WebSocket endpoints
│   │   ├── asr/                 ASR: whisper.cpp + MiniMax fallback
│   │   ├── tts/                 TTS: MiniMax t2a_v2 streaming
│   │   ├── llm/                 LLM: Claude -p streaming
│   │   ├── ha/                  HA REST API client + tools
│   │   └── conversation/        Multi-turn context + LanceDB memory
│   └── scripts/
├── clients/
│   ├── ios/                     SwiftUI iOS app
│   └── android/                 Kotlin + Compose Android app
├── integrations/
│   └── laopodada-bridge/        laopodada家居tab
└── deploy/                      launchd plist + install script
```

## Configuration

`~/.yuanfang-brain/config.yaml`:

```yaml
server_host: "0.0.0.0"
server_port: 7000
ws_port: 7001
whisper_model: tiny
ha:
  url: "http://192.168.1.10:8123"
  token: "<your-long-lived-token>"
minimax:
  api_key: "<your-api-key>"
  group_id: "<your-group-id>"
```

## WebSocket Protocol

Connect to `ws://<mac-ip>:7001/ws`

### Server → Client Messages

| type | data |
|---|---|
| `hello` | `{"conn_id", "server"}` |
| `transcript` | `{"text", "final"}` |
| `llm_chunk` | `{"text"}` |
| `llm_done` | `{}` |
| `tts_chunk` | `{"audio": "<base64 mp3>"}` |
| `tts_done` | `{}` |
| `pong` | `{}` |

### Client → Server Messages

Send raw PCM 16kHz/16bit/mono binary frames directly on the WebSocket.

## Supported Devices

- Lights (`light.*`)
- Switches (`switch.*`)
- Climate/HVAC (`climate.*`)
- Curtains/Covers (`cover.*`)
- Vacuum (`vacuum.*`)
- Door locks (`lock.*`)

## Key Features

- **Local-first**: ASR works offline via whisper.cpp (Metal GPU on M-series Mac)
- **Cloud fallback**: MiniMax ASR/TTS/LLM when local processing isn't available
- **Streaming**: VAD → ASR → LLM → TTS all stream token-by-token
- **Multi-turn memory**: LanceDB for long-term, SQLite for session history
- **HA-native**: Uses Home Assistant REST API, no custom integration needed
