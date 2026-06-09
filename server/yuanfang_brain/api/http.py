"""HTTP REST endpoints."""

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse

from yuanfang_brain import __version__
from yuanfang_brain.api.schema import HealthResponse


def create_router() -> APIRouter:
    router = APIRouter()

    @router.get("/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(version=__version__)

    @router.get("/version")
    async def version():
        return {"version": __version__}

    @router.get("/metrics")
    async def metrics():
        # Prometheus-style metrics endpoint for future Grafana integration
        return JSONResponse(
            content={
                "requests_total": 0,
                "requests_active": 0,
                "transcriptions_total": 0,
                "tts_tokens_total": 0,
                "llm_tokens_total": 0,
                "ha_calls_total": 0,
                "uptime_seconds": 0,
            }
        )

    return router


def create_app() -> FastAPI:
    app = FastAPI(title="yuanfang-brain", version=__version__)
    app.include_router(create_router())
    return app
