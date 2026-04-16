from __future__ import annotations

from typing import Any


class SSEEvent:
    """Lightweight container for a typed SSE event to yield from the generator."""

    __slots__ = ("event", "data")

    def __init__(self, event: str, data: dict[str, Any]) -> None:
        self.event = event
        self.data = data
