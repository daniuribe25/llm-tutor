from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from langfuse import observe

from api.config import MODEL
from api.services.agents.base import BaseAgent
from api.services.agents.prompts import SYNTHESIZER_PROMPT
from api.services.agents.researcher import ResearchResult
from api.services.ollama_client import get_client
from api.services.sse import SSEEvent

logger = logging.getLogger(__name__)


class Synthesizer(BaseAgent):
    """
    Integrates all research results into a single coherent response.

    In streaming mode: yields text SSEEvents directly to the user.
    In non-streaming mode: returns the full text for the Critic to evaluate.
    """

    async def synthesize(
        self,
        original_query: str,
        research_results: list[ResearchResult],
        *,
        stream: bool = False,
        conversation_context: list[dict[str, Any]] | None = None,
        think: str | None = None,
    ) -> str | AsyncIterator[SSEEvent]:
        """
        Produce a comprehensive answer from all research findings.

        Args:
            original_query: The user's original question.
            research_results: All findings from the researcher agents.
            stream: If True, stream text events. If False, return full string.
            conversation_context: Recent conversation history for context.
            think: Optional Ollama thinking mode to pass through.
        """
        messages = self._build_messages(original_query, research_results, conversation_context)

        if stream:
            return self._stream_synthesis(messages, think=think)
        else:
            return await self._collect_synthesis(messages, think=think)

    def _build_messages(
        self,
        query: str,
        results: list[ResearchResult],
        conversation_context: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        research_block = "\n\n---\n\n".join(r.as_context_block() for r in results)

        context_block = ""
        if conversation_context:
            recent = [
                m for m in conversation_context[-6:]
                if m.get("role") in ("user", "assistant") and m.get("content")
            ]
            if len(recent) > 1:
                lines = [
                    f"[{m['role'].upper()}]: {m['content'][:400]}"
                    for m in recent[:-1]  # exclude last (current query)
                ]
                context_block = (
                    "\n\nConversation history (for context):\n"
                    + "\n".join(lines)
                    + "\n"
                )

        user_content = (
            f"Original user question:{context_block}\n\n"
            f"**{query}**\n\n"
            f"---\n\n"
            f"Research findings from your team:\n\n"
            f"{research_block}\n\n"
            f"---\n\n"
            f"Now write the comprehensive, definitive response for the user."
        )

        return [
            {"role": "system", "content": SYNTHESIZER_PROMPT},
            {"role": "user", "content": user_content},
        ]

    @observe(name="synthesizer.collect", as_type="generation")
    async def _collect_synthesis(
        self, messages: list[dict[str, Any]], *, think: str | None = None
    ) -> str:
        """Non-streaming synthesis for use before critique."""
        client = get_client()
        kwargs: dict[str, Any] = dict(model=MODEL, messages=messages, stream=False)
        if think and think in ("low", "medium", "high"):
            kwargs["think"] = think
        response = await client.chat(**kwargs)
        return response.message.content or ""

    async def _stream_synthesis(
        self, messages: list[dict[str, Any]], *, think: str | None = None
    ) -> AsyncIterator[SSEEvent]:
        """Streaming synthesis that yields text SSEEvents directly to the user."""
        client = get_client()
        kwargs: dict[str, Any] = dict(model=MODEL, messages=messages, stream=True)
        if think and think in ("low", "medium", "high"):
            kwargs["think"] = think
        stream = await client.chat(**kwargs)
        async for chunk in stream:
            msg = chunk.message
            if msg and msg.content:
                yield SSEEvent("text", {"content": msg.content})
