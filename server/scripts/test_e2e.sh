#!/bin/bash
# End-to-end smoke test for yuanfang-brain server

set -e

HOST="${1:-localhost}"
PORT="${2:-7000}"
WSPORT="${3:-7001}"

echo "=== Yuanfang-brain E2E Smoke Test ==="

# 1. Health check
echo "[1/3] Testing /health..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://$HOST:$PORT/health")
if [ "$STATUS" = "200" ]; then
    echo "  ✓ /health returns 200"
else
    echo "  ✗ /health returned $STATUS"
    exit 1
fi

VERSION=$(curl -s "http://$HOST:$PORT/health" | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])")
echo "  ✓ version=$VERSION"

# 2. /version endpoint
echo "[2/3] Testing /version..."
VERSION2=$(curl -s "http://$HOST:$PORT/version" | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])")
if [ "$VERSION" = "$VERSION2" ]; then
    echo "  ✓ /version OK"
else
    echo "  ✗ version mismatch"
    exit 1
fi

# 3. WebSocket hello
echo "[3/3] Testing WebSocket hello..."
if command -v websocat &>/dev/null; then
    WS_RESP=$(echo '{"type":"hello"}' | timeout 5 websocat "ws://$HOST:$WSPORT/ws" --text-mode -)
    if echo "$WS_RESP" | grep -q '"type":"hello"'; then
        echo "  ✓ WS hello received"
    else
        echo "  ✗ WS response: $WS_RESP"
        exit 1
    fi
else
    echo "  ⚠ websocat not found, skipping WS test"
fi

echo ""
echo "=== All smoke tests passed ==="
