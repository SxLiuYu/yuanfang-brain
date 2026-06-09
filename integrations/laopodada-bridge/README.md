# laopodada-bridge

Integrates yuanfang-brain smart home control into the laopodada app.

## How It Works

The `www/` directory contains a standalone HTML家居tab that can be
dropped into the laopodada `www/` directory.

It communicates with yuanfang-brain via its HTTP API on the Mac:

- `GET /api/ha/entities` — list all HA entities
- `POST /api/ha/service/{domain}/{action}` — call a service (turn_on/turn_off)

## Integration

```bash
# From the laopodada repo:
cd /path/to/laopodada
cp -r yuanfang-brain/integrations/laopodada-bridge/www/* www/
```

The tab will automatically connect to `http://192.168.1.10:7000` (configurable).

## Standalone

Can also run as a standalone web page without laopodada:

```bash
open integrations/laopodada-bridge/www/index.html
```
