from __future__ import annotations

import logging
from typing import Any, Literal

from api.services.agents.base import BaseAgent
from api.services.agents.prompts import ROUTER_PROMPT

logger = logging.getLogger(__name__)

Classification = Literal["DIRECT", "RESEARCH_LITE", "RESEARCH_DEEP"]

_VALID = {"DIRECT", "RESEARCH_LITE", "RESEARCH_DEEP"}


class QueryRouter(BaseAgent):
    """
    Classifies the user's query to determine the appropriate processing pipeline.

    Uses only the last few messages for context to keep latency minimal —
    this is the fastest agent in the pipeline.
    """

    async def classify(
        self,
        messages: list[dict[str, Any]],
        *,
        context_window: int = 3,
    ) -> Classification:
        """
        Classify the query from the tail of the conversation history.

        Returns one of: DIRECT, RESEARCH_LITE, RESEARCH_DEEP
        Falls back to RESEARCH_LITE on any error.
        """
        # Use only the last N messages for efficiency
        recent = messages[-context_window:] if len(messages) > context_window else messages

        prompt_messages = [
            {"role": "system", "content": ROUTER_PROMPT},
            {
                "role": "user",
                "content": (
                    "Classify the following conversation. "
                    "Focus on the LAST user message.\n\n"
                    + _format_context(recent)
                ),
            },
        ]

        result = await self.call_llm_json(
            prompt_messages,
            schema_hint='{"classification": "DIRECT|RESEARCH_LITE|RESEARCH_DEEP", "reasoning": "..."}',
        )

        raw = str(result.get("classification", "RESEARCH_LITE")).upper().strip()
        classification: Classification = raw if raw in _VALID else "RESEARCH_LITE"  # type: ignore[assignment]

        logger.info("Router classified query as %s: %s", classification, result.get("reasoning", ""))
        return classification


def _format_context(messages: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if content:
            lines.append(f"[{role.upper()}]: {content[:500]}")
    return "\n".join(lines)
