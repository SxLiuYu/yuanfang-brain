"""LLM factory."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_llm: "ClaudeLLM | None" = None


def get_llm():
    global _llm
    if _llm is None:
        try:
            _llm = __import__("yuanfang_brain.llm.claude", fromlist=["ClaudeLLM"]).ClaudeLLM()
            logger.info("Claude LLM available")
        except Exception as e:
            logger.warning(f"LLM unavailable: {e}")
            _llm = None
    return _llm
