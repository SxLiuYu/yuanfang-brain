#!/bin/bash
# Start yuanfang-brain server

set -e

VENV="$HOME/.yuanfang-brain-venv"
CONFIG="$HOME/.yuanfang-brain/config.yaml"
PIDFILE="$HOME/.yuanfang-brain/server.pid"
LOG="$HOME/.yuanfang-brain/server.log"

# Ensure config exists
mkdir -p "$(dirname "$CONFIG")"
if [ ! -f "$CONFIG" ]; then
    cat > "$CONFIG" <<EOF
server_host: "0.0.0.0"
server_port: 7000
ws_port: 7001
log_level: INFO
whisper_model: tiny
ha:
  url: "http://192.168.1.10:8123"
  token: ""
minimax:
  api_key: ""
  group_id: ""
EOF
    echo "Created default config at $CONFIG"
fi

# Activate venv and start
if [ ! -d "$VENV" ]; then
    echo "Creating venv at $VENV..."
    python3.12 -m venv "$VENV"
fi

source "$VENV/bin/activate"
pip install -q -e "$HOME/repos/yuanfang-brain/server"

echo "Starting yuanfang-brain..."
nohup python -m yuanfang_brain.main > "$LOG" 2>&1 &
echo $! > "$PIDFILE"
echo "PID $(cat $PIDFILE) — logs at $LOG"
