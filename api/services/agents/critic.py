from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from langfuse import observe

from api.config import MODEL
from api.services.agents.base import BaseAgent
from api.services.agents.prompts import CRITIC_PROMPT, REFINER_PROMPT
from api.services.agents.researcher import ResearchResult
from api.services.ollama_client import get_client
from api.services.sse import SSEEvent

logger = logging.getLogger(__name__)

_REVISION_THRESHOLD = 7


@dataclass
class CritiqueResult:
    """Structured output from the Critic agent."""

    overall_score: float
    needs_revision: bool
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [f"Overall score: {self.overall_score}/10"]
        if self.issues:
            lines.append("Issues: " + "; ".join(self.issues[:3]))
        return " | ".join(lines)


class Critic(BaseAgent):
    """
    Evaluates a synthesized response for accuracy, completeness, clarity and depth.
    Triggers revision when quality falls below threshold.
    """

    @observe(name="critic.evaluate")
    async def evaluate(
        self,
        original_query: str,
        response: str,
        research_results: list[ResearchResult],
    ) -> CritiqueResult:
        """
        Critique the synthesized response.

        Returns a CritiqueResult indicating whether revision is needed.
        Falls back to a passing score on any parsing error.
        """
        research_block = "\n\n---\n\n".join(r.as_context_block() for r in research_results)

        messages = [
            {"role": "system", "content": CRITIC_PROMPT},
            {
                "role": "user",
                "content": (
                    f"## Original User Question\n{original_query}\n\n"
                    f"## Research Findings\n{research_block}\n\n"
                    f"## Response to Evaluate\n{response}\n\n"
                    "Evaluate this response rigorously."
                ),
            },
        ]

        result = await self.call_llm_json(
            messages,
            schema_hint='{"scores": {"accuracy": 0-10, "completeness": 0-10, "clarity": 0-10, "depth": 0-10}, "overall_score": 0-10, "needs_revision": true|false, "issues": [...], "suggestions": [...]}',
        )

        try:
            overall = float(result.get("overall_score", 8))
            needs_revision = bool(result.get("needs_revision", False))
            issues = [str(i) for i in result.get("issues", [])]
            suggestions = [str(s) for s in result.get("suggestions", [])]
            scores = {k: float(v) for k, v in result.get("scores", {}).items()}

            # Enforce threshold rule: any individual dimension < threshold also triggers revision
            dim_scores = list(scores.values())
            if dim_scores and min(dim_scores) < _REVISION_THRESHOLD:
                needs_revision = True

            critique = CritiqueResult(
                overall_score=overall,
                needs_revision=needs_revision,
                issues=issues,
                suggestions=suggestions,
                scores=scores,
            )
            logger.info("Critic evaluation: %s", critique.summary())
            return critique

        except Exception as exc:
            logger.warning("Critic parse error (%s), defaulting to no revision", exc)
            return CritiqueResult(overall_score=8.0, needs_revision=False)


class Refiner(BaseAgent):
    """
    Rewrites the synthesized response based on Critic feedback.
    Streams the improved answer directly as text SSEEvents.
    """

    async def refine(
        self,
        original_query: str,
        original_response: str,
        critique: CritiqueResult,
        research_results: list[ResearchResult],
    ) -> AsyncIterator[SSEEvent]:
        """
        Produce an improved response addressing all critic issues.
        Streams text SSEEvents.
        """
        research_block = "\n\n---\n\n".join(r.as_context_block() for r in research_results)
        issues_block = "\n".join(f"- {i}" for i in critique.issues)
        suggestions_block = "\n".join(f"- {s}" for s in critique.suggestions)

        messages = [
            {"role": "system", "content": REFINER_PROMPT},
            {
                "role": "user",
                "content": (
                    f"## Original User Question\n{original_query}\n\n"
                    f"## Research Findings\n{research_block}\n\n"
                    f"## Current Response (needs improvement)\n{original_response}\n\n"
                    f"## Critic's Issues\n{issues_block or '(none specified)'}\n\n"
                    f"## Critic's Suggestions\n{suggestions_block or '(none specified)'}\n\n"
                    "Produce the improved response now."
                ),
            },
        ]

        client = get_client()
        stream = await client.chat(
            model=MODEL,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            msg = chunk.message
            if msg and msg.content:
                yield SSEEvent("text", {"content": msg.content})
