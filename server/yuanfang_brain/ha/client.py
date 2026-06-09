"""Home Assistant REST API client."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from yuanfang_brain.config import get_config

logger = logging.getLogger(__name__)


class HAClient:
    """Client for Home Assistant REST API."""

    def __init__(self, url: str | None = None, token: str | None = None):
        cfg = get_config()
        self.url = (url or cfg.ha.url).rstrip("/")
        self.token = token or cfg.ha.token
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def get_state(self, entity_id: str) -> dict[str, Any]:
        """GET /api/states/{entity_id}."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.url}/api/states/{entity_id}",
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def list_entities(self, domain: str | None = None) -> list[dict[str, Any]]:
        """List all states, optionally filtered by domain."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.url}/api/states",
                headers=self._headers,
            )
            resp.raise_for_status()
            states = resp.json()
            if domain:
                return [s for s in states if s["entity_id"].startswith(f"{domain}.")]
            return states

    async def call_service(
        self, domain: str, service: str, entity_id: str | None = None, data: dict | None = None
    ) -> dict[str, Any]:
        """Call a Home Assistant service."""
        payload = {"domain": domain, "service": service}
        if entity_id:
            payload["entity_id"] = entity_id
        if data:
            payload["data"] = data

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self.url}/api/services/{domain}/{service}",
                headers=self._headers,
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def toggle(self, entity_id: str) -> dict[str, Any]:
        """Toggle a switch/light entity."""
        return await self.call_service(
            entity_id.split(".")[0], "toggle", entity_id=entity_id
        )
