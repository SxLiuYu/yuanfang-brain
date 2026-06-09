"""LanceDB memory store for long-term conversation memory."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_lancedb_available = False
_db = None


def _init_db():
    global _db, _lancedb_available
    if _db is not None:
        return _db
    try:
        import lancedb
        db_path = Path("~/.yuanfang-brain/lancedb").expanduser()
        db_path.mkdir(parents=True, exist_ok=True)
        _db = lancedb.connect(str(db_path))
        _lancedb_available = True
        logger.info(f"LanceDB initialized at {db_path}")
        return _db
    except ImportError:
        logger.warning("LanceDB not available, memory store disabled")
        _lancedb_available = False
        return None


async def store_memory(conversation_id: str, role: str, content: str, metadata: dict | None = None):
    """Store a memory entry in LanceDB."""
    db = _init_db()
    if db is None:
        return
    try:
        tbl = db.open_table("memory", create_if_missing=True)
        import pyarrow as pa
        tbl.add(
            pa.record_batch(
                {
                    "conversation_id": [conversation_id],
                    "role": [role],
                    "content": [content],
                    "metadata": [str(metadata or {})],
                }
            )
        )
    except Exception as e:
        logger.error(f"Failed to store memory: {e}")


async def recall_memories(query: str, limit: int = 5) -> list[str]:
    """Recall relevant memories based on semantic query."""
    db = _init_db()
    if db is None:
        return []
    try:
        tbl = db.open_table("memory")
        results = tbl.search(query, limit=limit).to_list()
        return [r["content"] for r in results]
    except Exception as e:
        logger.error(f"Failed to recall memories: {e}")
        return []
