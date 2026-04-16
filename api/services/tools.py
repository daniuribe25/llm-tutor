from __future__ import annotations

from typing import Any

from ollama import Tool

from api.services.ollama_client import get_client

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

WEB_FETCH_TOOL = Tool(
    type="function",
    function=Tool.Function(
        name="web_fetch",
        description="Fetch and read the full content of a specific web page URL. Use this after a web search when you need to read a page in depth to extract detailed information, code examples, or precise facts.",
        parameters=Tool.Function.Parameters(
            type="object",
            required=["url"],
            properties={
                "url": Tool.Function.Parameters.Property(
                    type="string",
                    description="The full URL of the web page to fetch and read.",
                ),
            },
        ),
    ),
)

# Tools available to the researcher agent (richer toolset than basic chat)
RESEARCHER_TOOLS = [SEARCH_TOOL, WEB_FETCH_TOOL]


def _format_search_results(results: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        url = r.get("url", "")
        content = r.get("content", "")
        parts.append(f"[{i}] {title}\n    URL: {url}\n    {content}")
    return "\n\n".join(parts)


async def execute_web_search(query: str) -> tuple[list[dict], str]:
    """Run a web search and return (raw_results, formatted_text)."""
    try:
        response = await get_client().web_search(query=query, max_results=5)
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


async def execute_web_fetch(url: str) -> tuple[dict, str]:
    """Fetch a specific web page and return (raw_result, formatted_text)."""
    try:
        response = await get_client().web_fetch(url=url)
        content = getattr(response, "content", None) or str(response)
        # Truncate very long pages to avoid context overflow
        truncated = content[:8000] if len(content) > 8000 else content
        raw = {"title": f"Full page: {url}", "url": url, "content": truncated}
        formatted = f"Content from {url}:\n\n{truncated}"
        return raw, formatted
    except Exception as exc:
        raw = {"title": "Fetch error", "url": url, "content": f"Fetch error: {exc}"}
        return raw, f"Web fetch failed for {url}: {exc}"
