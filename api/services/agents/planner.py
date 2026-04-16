from __future__ import annotations

import logging
from typing import Any

from api.services.agents.base import BaseAgent
from api.services.agents.prompts import PLANNER_PROMPT

logger = logging.getLogger(__name__)

_MIN_SUB_QUESTIONS = 2
_MAX_SUB_QUESTIONS = 5


class QueryPlanner(BaseAgent):
    """
    Decomposes a complex user query into focused, searchable sub-questions.

    Each sub-question is designed to be independently researched by a
    Researcher agent, with all results later synthesized into a final answer.
    """

    async def plan(
        self,
        query: str,
        *,
        conversation_context: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """
        Decompose the query into 2-5 focused sub-questions.

        Falls back to a single-item list with the original query on failure.
        """
        context_block = ""
        if conversation_context:
            recent = conversation_context[-4:]
            lines = [
                f"[{m.get('role', 'user').upper()}]: {m.get('content', '')[:300]}"
                for m in recent
                if m.get("role") != "system"
            ]
            if lines:
                context_block = (
                    "\n\nConversation context (for understanding the query):\n"
                    + "\n".join(lines)
                )

        prompt_messages = [
            {"role": "system", "content": PLANNER_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Decompose this query into focused sub-questions:{context_block}\n\n"
                    f"Query: {query}"
                ),
            },
        ]

        result = await self.call_llm_json(
            prompt_messages,
            schema_hint='{"sub_questions": ["question 1", "question 2", ...]}',
        )

        raw_questions: list = result.get("sub_questions", [])

        # Validate and clamp
        questions = [str(q).strip() for q in raw_questions if str(q).strip()]
        questions = questions[:_MAX_SUB_QUESTIONS]

        if len(questions) < _MIN_SUB_QUESTIONS:
            logger.warning(
                "Planner returned %d sub-questions (min %d); falling back to original query",
                len(questions),
                _MIN_SUB_QUESTIONS,
            )
            return [query]

        logger.info("Planner produced %d sub-questions for: %s", len(questions), query[:80])
        return questions
