from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.models.schemas import Conversation, ConversationSummary, Message
from api.services.conversation_store import store

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummary])
async def list_conversations():
    return store.list_all()


@router.post("", response_model=Conversation)
async def create_conversation():
    return store.create()


@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    conv = store.get(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    if not store.delete(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True}
