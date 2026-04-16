from __future__ import annotations

"""
Multi-agent research orchestrator.

Selects and runs the appropriate pipeline based on query complexity:

  DIRECT         -> stream_chat (existing fast path, zero overhead)
  RESEARCH_LITE  -> plan -> sequential research -> stream synthesis
  RESEARCH_DEEP  -> plan -> parallel research -> synthesize -> critique -> (refine) -> stream
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from api.services.agents.critic import Critic, Refiner
from api.services.agents.planner import QueryPlanner
from api.services.agents.researcher import ResearchResult, Researcher
from api.services.agents.router import QueryRouter
from api.services.agents.synthesizer import Synthesizer
from api.services.ollama_service import stream_chat
from api.services.sse import SSEEvent

logger = logging.getLogger(__name__)


def _status(step: str, detail: str, progress: float) -> SSEEvent:
    """Convenience factory for pipeline_status events."""
    return SSEEvent("pipeline_status", {"step": step, "detail": detail, "progress": progress})


async def orchestrate(
    messages: list[dict[str, Any]],
    *,
    think: str | None = None,
    research_mode: str | None = None,
) -> AsyncIterator[SSEEvent]:
    """
    Main entry point for the multi-agent research pipeline.

    Wraps the full pipeline in error handling so the frontend always
    receives either content or a clean error event.
    """
    try:
        async for event in _orchestrate_inner(messages, think=think, research_mode=research_mode):
            yield event
    except Exception as exc:
        logger.exception("Orchestrator error")
        yield SSEEvent("error", {"error": str(exc)})


async def _orchestrate_inner(
    messages: list[dict[str, Any]],
    *,
    think: str | None = None,
    research_mode: str | None = None,
) -> AsyncIterator[SSEEvent]:
    last_user_query = _last_user_message(messages)

    # --- Step 1: Route ---
    if research_mode == "deep":
        classification = "RESEARCH_DEEP"
        logger.info("Research mode forced to RESEARCH_DEEP by user")
    else:
        yield _status("routing", "Analyzing your question...", 0.02)
        router = QueryRouter()
        classification = await router.classify(messages)
        logger.info("Orchestrator routing to: %s", classification)

    # --- DIRECT path: hand off to existing stream_chat unchanged ---
    if classification == "DIRECT":
        async for event in stream_chat(messages, think=think):
            yield event
        return

    # --- RESEARCH paths ---
    yield _status("planning", "Breaking down your question into research tasks...", 0.08)

    planner = QueryPlanner()
    sub_questions = await planner.plan(
        last_user_query,
        conversation_context=messages,
    )
    logger.info("Planner produced %d sub-questions", len(sub_questions))

    total = len(sub_questions)

    if classification == "RESEARCH_LITE":
        async for event in _run_lite(
            last_user_query, sub_questions, messages, total, think=think
        ):
            yield event
        return

    async for event in _run_deep(
        last_user_query, sub_questions, messages, total, think=think
    ):
        yield event


# ---------------------------------------------------------------------------
# RESEARCH_LITE pipeline
# ---------------------------------------------------------------------------

async def _run_lite(
    query: str,
    sub_questions: list[str],
    messages: list[dict[str, Any]],
    total: int,
    *,
    think: str | None = None,
) -> AsyncIterator[SSEEvent]:
    researcher = Researcher()
    synthesizer = Synthesizer()
    all_results: list[ResearchResult] = []

    for i, question in enumerate(sub_questions):
        progress = 0.15 + (i / total) * 0.50
        yield _status(
            "researching",
            f"Researching: {question[:80]}{'...' if len(question) > 80 else ''} ({i + 1}/{total})",
            progress,
        )

        async for item in researcher.research(question):
            if isinstance(item, ResearchResult):
                all_results.append(item)
            else:
                yield item

    yield _status("synthesizing", "Writing your answer...", 0.80)

    synthesis_gen = await synthesizer.synthesize(
        query, all_results, stream=True, conversation_context=messages, think=think
    )
    async for event in synthesis_gen:
        yield event


# ---------------------------------------------------------------------------
# RESEARCH_DEEP pipeline
# ---------------------------------------------------------------------------

async def _run_deep(
    query: str,
    sub_questions: list[str],
    messages: list[dict[str, Any]],
    total: int,
    *,
    think: str | None = None,
) -> AsyncIterator[SSEEvent]:
    yield _status(
        "researching",
        f"Running {total} research tasks in parallel...",
        0.15,
    )

    results_and_events = await _parallel_research(sub_questions, total)
    all_results: list[ResearchResult] = []

    for item in results_and_events:
        if isinstance(item, ResearchResult):
            all_results.append(item)
        elif isinstance(item, SSEEvent):
            yield item

    yield _status("synthesizing", "Synthesizing findings into a comprehensive answer...", 0.72)

    synthesizer = Synthesizer()
    synthesis_text = await synthesizer.synthesize(
        query, all_results, stream=False, conversation_context=messages, think=think
    )
    if not isinstance(synthesis_text, str):
        synthesis_text = ""

    yield _status("critiquing", "Reviewing answer quality...", 0.85)

    critic = Critic()
    critique = await critic.evaluate(query, synthesis_text, all_results)
    logger.info("Critique: score=%.1f needs_revision=%s", critique.overall_score, critique.needs_revision)

    if critique.needs_revision:
        yield _status("refining", "Improving answer based on review...", 0.92)
        refiner = Refiner()
        async for event in refiner.refine(query, synthesis_text, critique, all_results):
            yield event
    else:
        yield _status("synthesizing", "Finalizing answer...", 0.95)
        for chunk in _chunk_text(synthesis_text, size=80):
            yield SSEEvent("text", {"content": chunk})


async def _parallel_research(
    sub_questions: list[str],
    total: int,
) -> list[SSEEvent | ResearchResult]:
    """Run all researcher agents concurrently, collecting events and results."""

    async def _collect_one(question: str, idx: int) -> list[SSEEvent | ResearchResult]:
        researcher = Researcher()
        items: list[SSEEvent | ResearchResult] = []
        async for item in researcher.research(question):
            items.append(item)
        return items

    tasks = [_collect_one(q, i) for i, q in enumerate(sub_questions)]
    grouped = await asyncio.gather(*tasks, return_exceptions=True)

    events: list[SSEEvent] = []
    results: list[ResearchResult] = []
    for group in grouped:
        if isinstance(group, BaseException):
            logger.warning("Researcher task failed: %s", group)
            continue
        for item in group:
            if isinstance(item, ResearchResult):
                results.append(item)
            else:
                events.append(item)

    return [*events, *results]


def _last_user_message(messages: list[dict[str, Any]]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user" and m.get("content"):
            return str(m["content"])
    return ""


def _chunk_text(text: str, size: int = 80) -> list[str]:
    """Split text into chunks for streaming simulation."""
    return [text[i : i + size] for i in range(0, len(text), size)]
