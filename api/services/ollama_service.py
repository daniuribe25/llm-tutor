from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from ollama import AsyncClient, Message as OllamaMessage, Tool

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

MODEL = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")

SYSTEM_PROMPT = """\
You are an expert tutor who helps users learn any topic they ask about.

Key behaviors:
- When a topic requires up-to-date or factual information, you MUST call the search_web tool to find the latest data before answering. This applies regardless of whether you are in thinking mode or not.
- Always prefer using search_web over relying on your training data for factual claims, current events, technical documentation, or anything that could be outdated.
- Explain concepts clearly, adapting to the user's level.
- Use examples, analogies, and step-by-step breakdowns.
- When the user sends images, analyze them and incorporate them into your teaching.
- Format responses with markdown: headings, bullet points, code blocks, bold/italic.
- If unsure, say so and suggest what to search for next.
- Be encouraging and patient.
"""

SEARCH_TOOL = Tool(
    type="function",
    function=Tool.Function(
        name="search_web",
        description="Search the web for current, accurate information on a topic. Use this when the user asks about facts, current events, technical details, or anything that benefits from up-to-date sources.",
        parameters=Tool.Function.Parameters(
            type="object",
            required=["query"],
            properties={
                "query": Tool.Function.Parameters.Property(
                    type="string",
                    description="The search query to look up on the web.",
                ),
            },
        ),
    ),
)


def _build_client() -> AsyncClient:
    model = MODEL
    if model.endswith("-cloud"):
        host = "https://ollama.com"
        if not os.environ.get("OLLAMA_API_KEY"):
            raise RuntimeError("OLLAMA_API_KEY is required for cloud models")
    else:
        host = os.environ.get("OLLAMA_HOST")
    return AsyncClient(host=host) if host else AsyncClient()


_client: AsyncClient | None = None


def _get_client() -> AsyncClient:
    """Lazy client so the API process can start (e.g. /health) before OLLAMA_API_KEY is validated."""
    global _client
    if _client is None:
        _client = _build_client()
    return _client


def _format_search_results(results: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        url = r.get("url", "")
        content = r.get("content", "")
        parts.append(f"[{i}] {title}\n    URL: {url}\n    {content}")
    return "\n\n".join(parts)


async def _execute_web_search(query: str) -> tuple[list[dict], str]:
    """Run a web search and return (raw_results, formatted_text)."""
    try:
        response = await _get_client().web_search(query=query, max_results=5)
        raw = [
            {
                "title": r.title or "",
                "url": r.url or "",
                "content": (r.content or "")[:500],
            }
            for r in response.results
        ]
        return raw, _format_search_results(raw)
    except Exception as exc:
        error_result = [{"title": "Search error", "url": "", "content": str(exc)}]
        return error_result, f"Web search failed: {exc}"


class SSEEvent:
    """Lightweight container for a typed SSE event to yield from the generator."""

    __slots__ = ("event", "data")

    def __init__(self, event: str, data: dict[str, Any]) -> None:
        self.event = event
        self.data = data


async def stream_chat(
    messages: list[dict[str, Any]],
    think: str | None = None,
) -> AsyncIterator[SSEEvent]:
    """
    Stream a chat turn. Handles the tool-calling loop internally:
    if the model emits tool_calls, execute them and re-stream.
    Yields SSEEvent objects.
    """
    ollama_messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *messages,
    ]

    think_param: str | None = think if think in ("low", "medium", "high") else None

    max_tool_rounds = 3
    try:
        for _ in range(max_tool_rounds):
            collected_content: list[str] = []
            tool_calls_detected: list[dict] = []

            chat_kwargs: dict[str, Any] = dict(
                model=MODEL,
                messages=ollama_messages,
                tools=[SEARCH_TOOL],
                stream=True,
            )
            if think_param is not None:
                chat_kwargs["think"] = think_param

            stream = await _get_client().chat(**chat_kwargs)

            async for chunk in stream:
                msg = chunk.message
                if not msg:
                    continue

                if msg.thinking:
                    yield SSEEvent("thinking", {"content": msg.thinking})

                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_calls_detected.append({
                            "name": tc.function.name,
                            "arguments": dict(tc.function.arguments),
                        })

                if msg.content:
                    collected_content.append(msg.content)
                    yield SSEEvent("text", {"content": msg.content})

            if not tool_calls_detected:
                break

            full_text = "".join(collected_content)
            ollama_messages.append({
                "role": "assistant",
                "content": full_text or "",
                "tool_calls": [
                    {"function": tc} for tc in tool_calls_detected
                ],
            })

            for tc in tool_calls_detected:
                query = tc["arguments"].get("query", "")
                yield SSEEvent("tool_call", {"name": tc["name"], "query": query})

                raw_results, formatted = await _execute_web_search(query)
                yield SSEEvent("search_results", {"results": raw_results})

                ollama_messages.append({
                    "role": "tool",
                    "content": formatted,
                })

            collected_content.clear()
            tool_calls_detected.clear()

    except Exception as exc:
        yield SSEEvent("error", {"error": str(exc)})
