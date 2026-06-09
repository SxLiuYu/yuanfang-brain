#!/bin/bash
# Copy laopodada-bridge家居tab into laopodada www directory
# Usage: ./sync.sh /path/to/laopodada/repo

set -e

LAOPODADA_DIR="${1:-}"

if [ -z "$LAOPODADA_DIR" ]; then
    echo "Usage: $0 /path/to/laopodada/repo"
    echo "No laopodada repo path provided — writing to ./www/ standalone"
    mkdir -p ~/repos/yuanfang-brain/integrations/laopodada-bridge/www
    exit 0
fi

DEST="$LAOPODADA_DIR/www"
if [ ! -d "$DEST" ]; then
    echo "laopodada www/ not found at $DEST"
    exit 1
fi

cp -r ~/repos/yuanfang-brain/integrations/laopodada-bridge/www/* "$DEST/"
echo "✓ Copied yuanfang-brain家居tab to $DEST"
