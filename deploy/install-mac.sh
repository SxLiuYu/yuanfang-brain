#!/bin/bash
# Install yuanfang-brain server as a launchd service on Mac

set -e

LABEL="com.yuanfang.brain"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
SERVER_DIR="$HOME/repos/yuanfang-brain/server"
VENV="$HOME/.yuanfang-brain-venv"
CONFIG="$HOME/.yuanfang-brain/config.yaml"

echo "=== Installing yuanfang-brain launchd service ==="

# Create config if needed
mkdir -p "$(dirname "$CONFIG")"
if [ ! -f "$CONFIG" ]; then
    cat > "$CONFIG" <<'EOF'
server_host: "0.0.0.0"
server_port: 7000
ws_port: 7001
log_level: INFO
whisper_model: tiny
ha:
  url: "http://192.168.1.10:8123"
  token: "ADD_YOUR_TOKEN_HERE"
minimax:
  api_key: "ADD_YOUR_KEY_HERE"
  group_id: "ADD_YOUR_GROUP_ID_HERE"
EOF
    echo "Created config at $CONFIG — please edit with your tokens"
fi

# Create venv
python3.12 -m venv "$VENV"
source "$VENV/bin/activate"
pip install -q fastapi uvicorn websockets pydantic pyyaml httpx pytest pytest-asyncio orjson aiofiles

# Create LaunchAgents dir
mkdir -p "$HOME/Library/LaunchAgents"

# Write plist
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList1-0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV/bin/python</string>,
        <string>-m</string>,
        <string>uvicorn</string>,
        <string>yuanfang_brain.main:create_app()</string>,
        <string>--factory</string>,
        <string>--host</string>,
        <string>0.0.0.0</string>,
        <string>--port</string>,
        <string>7000</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$SERVER_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>$SERVER_DIR</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/.yuanfang-brain/server.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.yuanfang-brain/server.log</string>
</dict>
</plist>
EOF

# Load the service
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "✓ Service loaded: $PLIST"
echo "  Logs: $HOME/.yuanfang-brain/server.log"
echo "  Start: launchctl start $LABEL"
echo "  Stop:  launchctl stop $LABEL"
