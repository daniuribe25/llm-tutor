from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from api.config import MODEL
from api.services.ollama_client import get_client
from api.services.prompts import SYSTEM_PROMPT
from api.services.sse import SSEEvent
from api.services.tools import SEARCH_TOOL, execute_web_search


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

            stream = await get_client().chat(**chat_kwargs)

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

                raw_results, formatted = await execute_web_search(query)
                yield SSEEvent("search_results", {"results": raw_results})

                ollama_messages.append({
                    "role": "tool",
                    "content": formatted,
                })

            collected_content.clear()
            tool_calls_detected.clear()

    except Exception as exc:
        yield SSEEvent("error", {"error": str(exc)})
