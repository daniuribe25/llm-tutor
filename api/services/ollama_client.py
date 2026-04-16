from __future__ import annotations

import os

from ollama import AsyncClient

from api.config import MODEL


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


def get_client() -> AsyncClient:
    """Lazy client so the API process can start (e.g. /health) before OLLAMA_API_KEY is validated."""
    global _client
    if _client is None:
        _client = _build_client()
    return _client
