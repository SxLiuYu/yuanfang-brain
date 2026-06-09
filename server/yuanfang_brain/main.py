"""Main FastAPI application entry point for yuanfang-brain server."""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from yuanfang_brain import __version__
from yuanfang_brain.api import http, ws
from yuanfang_brain.config import get_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"yuanfang-brain v{__version__} starting...")
    cfg = get_config()
    logger.info(f"Config: HA={cfg.ha.url}, WS port={cfg.ws_port}")
    yield
    logger.info("yuanfang-brain shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(title="yuanfang-brain", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(http.create_router(), tags=["http"])
    app.include_router(ws.create_router(), tags=["websocket"])
    return app


def main():
    cfg = get_config()
    app = create_app()
    uvicorn.run(
        app,
        host=cfg.server_host,
        port=cfg.server_port,
        log_level=cfg.log_level.lower(),
    )


if __name__ == "__main__":
    main()
