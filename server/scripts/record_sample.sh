#!/bin/bash
# Record a sample audio for testing ASR
# Usage: ./record_sample.sh [duration_secs]

set -e

DURATION="${1:-5}"
FILE="/tmp/sample_${DURATION}s.wav"

if command -v arecord &>/dev/null; then
    echo "Recording ${DURATION}s to $FILE..."
    arecord -f S16_LE -r 16000 -c 1 -d "$DURATION" "$FILE"
    echo "Saved: $FILE"
elif command -v ffmpeg &>/dev/null; then
    echo "Recording ${DURATION}s to $FILE using ffmpeg..."
    ffmpeg -f avfoundation -i ":0" -ar 16000 -ac 1 -t "$DURATION" "$FILE" -y -loglevel error
    echo "Saved: $FILE"
else
    echo "No audio recording tool found (arecord or ffmpeg)"
    exit 1
fi
