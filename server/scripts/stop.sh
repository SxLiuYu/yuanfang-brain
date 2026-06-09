#!/bin/bash
# Stop yuanfang-brain server

PIDFILE="$HOME/.yuanfang-brain/server.pid"
LOG="$HOME/.yuanfang-brain/server.log"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping yuanfang-brain (PID $PID)..."
        kill "$PID"
        sleep 1
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID"
        fi
    else
        echo "Process $PID not running"
    fi
    rm -f "$PIDFILE"
else
    echo "No PID file at $PIDFILE"
fi
