from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent

from api.models.schemas import ChatRequest, Message, Source, ToolCallRecord
from api.services.agents.orchestrator import orchestrate
from api.services.conversation_store import store

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_class=EventSourceResponse)
async def chat(body: ChatRequest, request: Request) -> AsyncIterator[ServerSentEvent]:
    if body.conversation_id:
        conv = store.get(body.conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conv = store.create()

    user_msg = Message(role="user", content=body.message, images=body.images)
    store.add_message(conv.id, user_msg)

    history = [_msg_to_ollama(m) for m in store.get_messages(conv.id)]

    full_response: list[str] = []
    thinking_parts: list[str] = []
    tool_calls_collected: list[ToolCallRecord] = []
    sources_collected: list[Source] = []

    async for sse_event in orchestrate(
        history, think=body.think, research_mode=body.research_mode
    ):
        if await request.is_disconnected():
            break

        if sse_event.event == "text":
            full_response.append(sse_event.data["content"])
        elif sse_event.event == "thinking":
            thinking_parts.append(sse_event.data["content"])
        elif sse_event.event == "tool_call":
            tool_calls_collected.append(
                ToolCallRecord(name=sse_event.data["name"], query=sse_event.data["query"])
            )
        elif sse_event.event == "search_results":
            for r in sse_event.data.get("results", []):
                sources_collected.append(
                    Source(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        content=r.get("content", ""),
                    )
                )

        yield ServerSentEvent(
            data=sse_event.data,
            event=sse_event.event,
        )

    assistant_text = "".join(full_response)
    if assistant_text or thinking_parts:
        store.add_message(
            conv.id,
            Message(
                role="assistant",
                content=assistant_text,
                thinking="".join(thinking_parts) or None,
                tool_calls=tool_calls_collected or None,
                sources=sources_collected or None,
            ),
        )

    updated_conv = store.get(conv.id)
    yield ServerSentEvent(
        data={
            "conversation_id": conv.id,
            "title": updated_conv.title if updated_conv else conv.title,
        },
        event="done",
    )


def _msg_to_ollama(msg: Message) -> dict:
    d: dict = {"role": msg.role, "content": msg.content}
    if msg.images:
        d["images"] = msg.images
    return d
