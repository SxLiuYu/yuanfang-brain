"""Claude LLM streaming via claude -p with --output-format stream-json."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from typing import AsyncGenerator, AsyncIterator

from yuanfang_brain.config import get_config
from yuanfang_brain.conversation.manager import get_conversation_manager

logger = logging.getLogger(__name__)


class ClaudeLLM:
    """Claude via CLI (-p) with streaming JSON output."""

    def __init__(self, model: str = "claude-opus-4-8"):
        cfg = get_config()
        self.api_key = cfg.minimax.api_key  # May be empty; claude -p uses own key
        self.model = model

    def _build_system(self) -> str:
        return """You are yuanfang-brain, a helpful local home assistant.
You control Home Assistant devices: lights, switches, climate, curtains, vacuum, door locks.
You have these tools available:
- ha_list_entities(domain): List HA entities
- ha_get_state(entity_id): Get entity state
- ha_toggle(entity_id): Toggle entity on/off
- ha_call_service(domain, service, entity_id, data): Call HA service

When the user asks to control something ("open the light", "turn on AC"), use the appropriate tool.
Keep responses concise and spoken-friendly (short sentences).
Always respond in Chinese unless the user speaks another language.
"""

    async def complete_stream(
        self, prompt: str, conn_id: str, system: str | None = None
    ) -> AsyncIterator[dict]:
        """Stream completion from Claude, yielding JSON chunks from --output-format stream-json."""
        manager = get_conversation_manager()
        history = manager.get_history(conn_id)

        # Build conversation context
        ctx_parts = []
        for msg in history:
            ctx_parts.append(f"Human: {msg.content}")
        ctx_parts.append(f"Human: {prompt}")
        context = "\n\n".join(ctx_parts)

        cmd = [
            "claude",
            "-p",
            context,
            "--model", self.model,
            "--output-format", "stream-json",
            "--system", system or self._build_system(),
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        accumulated = ""
        async for line in proc.stdout:
            line_str = line.decode().strip()
            if not line_str:
                continue
            accumulated += line_str
            # Each line from --output-format stream-json is a JSON object
            try:
                obj = json.loads(line_str)
                yield obj
            except json.JSONDecodeError:
                # Partial JSON, accumulate more
                continue

        await proc.wait()
        if proc.returncode != 0:
            stderr = await proc.stderr.read()
            logger.error(f"Claude error: {stderr.decode()}")

    async def complete(self, prompt: str, conn_id: str, system: str | None = None) -> str:
        """Get full completion text."""
        parts = []
        async for obj in self.complete_stream(prompt, conn_id, system):
            if obj.get("type") == "content_block_delta":
                delta = obj.get("delta", {})
                if isinstance(delta, dict):
                    text = delta.get("text", "")
                else:
                    text = str(delta)
                parts.append(text)
        return "".join(parts)
