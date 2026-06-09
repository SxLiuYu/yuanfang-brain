"""Conversation manager for multi-turn context and memory."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tool_calls: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)


@dataclass
class Conversation:
    id: str
    messages: list[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def add_user(self, content: str):
        self.messages.append(Message(role="user", content=content))

    def add_assistant(self, content: str, tool_calls=None, tool_results=None):
        self.messages.append(
            Message(role="assistant", content=content, tool_calls=tool_calls or [], tool_results=tool_results or [])
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "messages": [
                {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()}
                for m in self.messages
            ],
            "created_at": self.created_at.isoformat(),
        }


class ConversationManager:
    """Manages multi-turn conversations with context history."""

    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self._conversations: dict[str, Conversation] = {}
        self._current: dict[str, str] = {}  # conn_id -> conv_id

    def get_or_create(self, conn_id: str) -> Conversation:
        if conn_id not in self._current or self._current[conn_id] not in self._conversations:
            conv_id = str(uuid.uuid4())
            self._conversations[conv_id] = Conversation(id=conv_id)
            self._current[conn_id] = conv_id
        return self._conversations[self._current[conn_id]]

    def add_user_message(self, conn_id: str, content: str):
        conv = self.get_or_create(conn_id)
        conv.add_user(content)
        self._trim(conv)

    def add_assistant_message(self, conn_id: str, content: str, tool_calls=None, tool_results=None):
        conv = self.get_or_create(conn_id)
        conv.add_assistant(content, tool_calls, tool_results)
        self._trim(conv)

    def get_history(self, conn_id: str, limit: int = 20) -> list[Message]:
        conv = self.get_or_create(conn_id)
        return conv.messages[-limit:]

    def _trim(self, conv: Conversation):
        if len(conv.messages) > self.max_turns:
            conv.messages = conv.messages[-self.max_turns :]


_manager: ConversationManager | None = None


def get_conversation_manager() -> ConversationManager:
    global _manager
    if _manager is None:
        _manager = ConversationManager()
    return _manager
