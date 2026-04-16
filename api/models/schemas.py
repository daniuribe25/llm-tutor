from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    images: list[str] | None = None
    think: str | None = None


class MessageImage(BaseModel):
    data: str
    media_type: str = "image/png"


class Source(BaseModel):
    title: str = ""
    url: str = ""
    content: str = ""


class ToolCallRecord(BaseModel):
    name: str
    query: str


class Message(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    role: str
    content: str
    images: list[str] | None = None
    thinking: str | None = None
    tool_calls: list[ToolCallRecord] | None = Field(default=None, alias="toolCalls")
    sources: list[Source] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "New Chat"
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class SSETextEvent(BaseModel):
    content: str


class SSEToolCallEvent(BaseModel):
    name: str
    query: str


class SSESearchResultsEvent(BaseModel):
    results: list[dict]


class SSEDoneEvent(BaseModel):
    conversation_id: str


class SSEErrorEvent(BaseModel):
    error: str
