from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Any

from api.config import MODEL
from api.services.ollama_client import get_client

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _extract_json(text: str) -> str:
    """Strip markdown code fences if present, otherwise return the text as-is."""
    m = _JSON_FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text.strip()


class BaseAgent:
    """Shared LLM call logic for all agents in the pipeline."""

    async def call_llm(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[Any] | None = None,
        think: str | None = None,
        stream: bool = False,
    ) -> str | AsyncIterator[Any]:
        """Single LLM call. Returns full text or an async iterator when stream=True."""
        kwargs: dict[str, Any] = dict(
            model=MODEL,
            messages=messages,
            stream=stream,
        )
        if tools:
            kwargs["tools"] = tools
        if think and think in ("low", "medium", "high"):
            kwargs["think"] = think

        client = get_client()
        response = await client.chat(**kwargs)

        if stream:
            return response

        return response.message.content or ""

    async def call_llm_json(
        self,
        messages: list[dict[str, Any]],
        *,
        schema_hint: str | None = None,
        retries: int = 2,
    ) -> dict[str, Any]:
        """
        LLM call that returns a parsed JSON dict.
        Uses format='json' for reliable structured output.
        Falls back to text extraction + parsing on failure.
        """
        if schema_hint:
            messages = [
                *messages[:-1],
                {
                    **messages[-1],
                    "content": messages[-1]["content"]
                    + f"\n\nRespond with valid JSON matching this structure:\n{schema_hint}",
                },
            ]

        for attempt in range(retries + 1):
            try:
                client = get_client()
                response = await client.chat(
                    model=MODEL,
                    messages=messages,
                    format="json",
                    stream=False,
                )
                raw = response.message.content or "{}"
                extracted = _extract_json(raw)
                return json.loads(extracted)
            except json.JSONDecodeError as exc:
                logger.warning(
                    "JSON parse failed on attempt %d/%d: %s",
                    attempt + 1,
                    retries + 1,
                    exc,
                )
                if attempt == retries:
                    logger.error("All JSON parse attempts exhausted, returning empty dict")
                    return {}
            except Exception as exc:
                logger.warning(
                    "LLM call failed on attempt %d/%d: %s",
                    attempt + 1,
                    retries + 1,
                    exc,
                )
                if attempt == retries:
                    logger.error("All LLM call attempts exhausted, returning empty dict")
                    return {}

        return {}
