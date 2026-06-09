"""HA tools exposed to LLM for tool-calling."""

from __future__ import annotations

import logging
from typing import Any

from yuanfang_brain.ha.client import HAClient

logger = logging.getLogger(__name__)

_ha_client: HAClient | None = None


def get_ha_client() -> HAClient:
    global _ha_client
    if _ha_client is None:
        _ha_client = HAClient()
    return _ha_client


def register_ha_tools() -> list[dict[str, Any]]:
    """Return HA tool definitions for LLM function-calling."""

    async def ha_list_entities(domain: str | None = None) -> str:
        """List entities in Home Assistant. Optionally filter by domain (light, switch, climate, etc)."""
        client = get_ha_client()
        entities = await client.list_entities(domain)
        lines = [f"{e['entity_id']}: {e['state']}" for e in entities]
        return "\n".join(lines) if lines else "No entities found"

    async def ha_get_state(entity_id: str) -> str:
        """Get the current state of a specific entity."""
        client = get_ha_client()
        state = await client.get_state(entity_id)
        return f"{state['entity_id']}: {state['state']} ({state.get('attributes', {})})"

    async def ha_toggle(entity_id: str) -> str:
        """Toggle a light, switch, or other toggleable entity on/off."""
        client = get_ha_client()
        result = await client.toggle(entity_id)
        return f"Toggled {entity_id}: {result}"

    async def ha_call_service(
        domain: str, service: str, entity_id: str | None = None, data: dict | None = None
    ) -> str:
        """Call any Home Assistant service directly."""
        client = get_ha_client()
        result = await client.call_service(domain, service, entity_id, data)
        return f"Service called: {result}"

    return [
        {
            "name": "ha_list_entities",
            "description": "List Home Assistant entities. Optional domain filter (light, switch, climate, cover, vacuum, lock, etc).",
            "parameters": {
                "type": "object",
                "properties": {"domain": {"type": "string", "description": "Entity domain (e.g. light, switch)"}},
                "required": [],
            },
            "fn": ha_list_entities,
        },
        {
            "name": "ha_get_state",
            "description": "Get current state of a specific entity by entity_id.",
            "parameters": {
                "type": "object",
                "properties": {"entity_id": {"type": "string", "description": "e.g. light.living_room"}},
                "required": ["entity_id"],
            },
            "fn": ha_get_state,
        },
        {
            "name": "ha_toggle",
            "description": "Toggle a light, switch, or toggleable entity on/off.",
            "parameters": {
                "type": "object",
                "properties": {"entity_id": {"type": "string", "description": "e.g. light.living_room"}},
                "required": ["entity_id"],
            },
            "fn": ha_toggle,
        },
        {
            "name": "ha_call_service",
            "description": "Call any Home Assistant service directly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "service": {"type": "string"},
                    "entity_id": {"type": "string"},
                    "data": {"type": "object"},
                },
                "required": ["domain", "service"],
            },
            "fn": ha_call_service,
        },
    ]
