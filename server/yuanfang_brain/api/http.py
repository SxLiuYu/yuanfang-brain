"""HTTP REST endpoints."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from yuanfang_brain import __version__
from yuanfang_brain.api.schema import HealthResponse
from yuanfang_brain.ha.client import HAClient
from yuanfang_brain.ha.tools import get_ha_client


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

    # HA proxy endpoints for laopodada家居tab
    @router.get("/api/ha/entities")
    async def ha_list_entities(domain: str | None = None):
        """List HA entities, optionally filtered by domain."""
        try:
            client: HAClient = get_ha_client()
            entities = await client.list_entities(domain)
            return {"entities": entities}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/api/ha/entity/{entity_id}")
    async def ha_get_entity(entity_id: str):
        """Get single entity state."""
        try:
            client = get_ha_client()
            state = await client.get_state(entity_id)
            return state
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/api/ha/service/{domain}/{service}")
    async def ha_call(domain: str, service: str, entity_id: str | None = None, data: dict | None = None):
        """Call HA service directly."""
        try:
            client = get_ha_client()
            result = await client.call_service(domain, service, entity_id, data or {})
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router


def create_app() -> FastAPI:
    app = FastAPI(title="yuanfang-brain", version=__version__)
    app.include_router(create_router())
    return app
