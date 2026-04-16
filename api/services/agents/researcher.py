from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from langfuse import observe

from api.services.agents.base import BaseAgent
from api.services.agents.prompts import RESEARCHER_PROMPT
from api.services.sse import SSEEvent
from api.services.tools import (
    RESEARCHER_TOOLS,
    execute_web_fetch,
    execute_web_search,
)

logger = logging.getLogger(__name__)

_MAX_SEARCH_ROUNDS = 3


@dataclass
class ResearchResult:
    """Structured output from a single Researcher agent run."""

    question: str
    summary: str
    sources: list[dict[str, str]] = field(default_factory=list)
    search_queries_used: list[str] = field(default_factory=list)

    def as_context_block(self) -> str:
        """Format for use as input context to Synthesizer/Critic agents."""
        sources_block = "\n".join(
            f"  - {s.get('title', s.get('url', 'Unknown'))}: {s.get('url', '')}"
            for s in self.sources
        )
        queries_block = ", ".join(f'"{q}"' for q in self.search_queries_used)
        return (
            f"## Research: {self.question}\n\n"
            f"{self.summary}\n\n"
            f"**Search queries used:** {queries_block or 'none'}\n"
            f"**Sources consulted:**\n{sources_block or '  (none)'}"
        )


class Researcher(BaseAgent):
    """
    ReAct-style researcher that iteratively searches and fetches to answer a sub-question.

    Yields SSEEvents for real-time progress (tool_call, search_results).
    Accumulates findings across multiple search rounds before producing a final summary.
    """

    async def research(
        self,
        sub_question: str,
    ) -> AsyncIterator[SSEEvent | ResearchResult]:
        """
        Research a single sub-question using a ReAct loop.

        Yields SSEEvents during research (for frontend progress updates),
        then yields a single ResearchResult as the final item.
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": RESEARCHER_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Research this specific question thoroughly:\n\n{sub_question}\n\n"
                    "Use the search_web and web_fetch tools as needed, then produce your "
                    "structured research summary."
                ),
            },
        ]

        seen_urls: set[str] = set()
        all_sources: list[dict[str, str]] = []
        all_queries: list[str] = []
        final_summary: str = ""

        for round_num in range(_MAX_SEARCH_ROUNDS):
            logger.debug(
                "Researcher round %d/%d for: %s",
                round_num + 1,
                _MAX_SEARCH_ROUNDS,
                sub_question[:60],
            )

            response = await self._chat_with_tools(messages)
            msg = response.message if hasattr(response, "message") else response

            if msg.tool_calls:
                tool_messages, events = await self._execute_tools(
                    msg.tool_calls, all_sources, all_queries, seen_urls
                )

                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {"function": {"name": tc.function.name, "arguments": self._safe_args(tc)}}
                        for tc in msg.tool_calls
                    ],
                })
                messages.extend(tool_messages)

                for event in events:
                    yield event

            else:
                final_summary = msg.content or ""
                break

            if round_num == _MAX_SEARCH_ROUNDS - 1:
                messages.append({
                    "role": "user",
                    "content": (
                        "You have completed your allowed search rounds. "
                        "Now produce your structured research summary based on everything you've found."
                    ),
                })
                final_response = await self._chat_with_tools(messages, force_text=True)
                final_msg = final_response.message if hasattr(final_response, "message") else final_response
                final_summary = final_msg.content or ""

        if not final_summary:
            final_summary = f"No research findings available for: {sub_question}"

        yield ResearchResult(
            question=sub_question,
            summary=final_summary,
            sources=all_sources,
            search_queries_used=all_queries,
        )

    @staticmethod
    def _safe_args(tc: Any) -> dict[str, Any]:
        """Safely extract tool call arguments regardless of type."""
        try:
            return dict(tc.function.arguments)
        except (TypeError, ValueError):
            return {}

    @observe(name="researcher.chat_with_tools", as_type="generation")
    async def _chat_with_tools(self, messages: list[dict[str, Any]], *, force_text: bool = False):
        """Single LLM call with researcher tools, optionally without tools (force text)."""
        from api.config import MODEL
        from api.services.ollama_client import get_client

        kwargs: dict[str, Any] = dict(
            model=MODEL,
            messages=messages,
            stream=False,
        )
        if not force_text:
            kwargs["tools"] = RESEARCHER_TOOLS

        client = get_client()
        return await client.chat(**kwargs)

    async def _execute_tools(
        self,
        tool_calls: Any,
        all_sources: list[dict[str, str]],
        all_queries: list[str],
        seen_urls: set[str],
    ) -> tuple[list[dict[str, Any]], list[SSEEvent]]:
        """
        Execute all tool calls from a model response.

        Returns:
            - List of role="tool" messages to append to the conversation.
            - List of SSEEvents for frontend progress.
        """
        tool_messages: list[dict[str, Any]] = []
        events: list[SSEEvent] = []

        for tc in tool_calls:
            name = tc.function.name
            args = self._safe_args(tc)

            if name == "search_web":
                query = args.get("query", "")
                all_queries.append(query)

                events.append(SSEEvent("tool_call", {"name": "search_web", "query": query}))

                raw_results, formatted = await execute_web_search(query)

                for r in raw_results:
                    url = r.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_sources.append({"title": r.get("title", ""), "url": url})

                events.append(SSEEvent("search_results", {"results": raw_results}))
                tool_messages.append({"role": "tool", "content": formatted})

            elif name == "web_fetch":
                url = args.get("url", "")

                events.append(SSEEvent("tool_call", {"name": "web_fetch", "query": url}))

                raw_result, formatted = await execute_web_fetch(url)

                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_sources.append({"title": f"Full page: {url}", "url": url})

                events.append(SSEEvent("search_results", {"results": [raw_result] if raw_result else []}))
                tool_messages.append({"role": "tool", "content": formatted})

            else:
                logger.warning("Unknown tool call: %s", name)
                tool_messages.append({
                    "role": "tool",
                    "content": f"Error: Unknown tool '{name}'. Use search_web or web_fetch.",
                })

        return tool_messages, events
