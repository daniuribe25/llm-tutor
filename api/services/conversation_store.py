from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

from api.models.schemas import Conversation, ConversationSummary, Message, Source, ToolCallRecord

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _dt_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse_dt(s: str | datetime) -> datetime:
    if isinstance(s, datetime):
        if s.tzinfo is None:
            return s.replace(tzinfo=timezone.utc)
        return s
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is required. "
            "Example: postgresql://user:pass@host:5432/dbname"
        )
    return url


class ConversationStore:
    """Thread-safe PostgreSQL-backed conversation store."""

    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or _get_database_url()
        self._init_schema()

    @contextmanager
    def _connect(self):
        conn = psycopg2.connect(self._database_url)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        conversation_id TEXT NOT NULL
                            REFERENCES conversations(id) ON DELETE CASCADE,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        images_json TEXT,
                        thinking TEXT,
                        tool_calls_json TEXT,
                        sources_json TEXT,
                        timestamp TIMESTAMPTZ NOT NULL,
                        sort_order INTEGER NOT NULL
                    )
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_conversation
                        ON messages (conversation_id, sort_order)
                """)

    def create(self, title: str = "New Chat") -> Conversation:
        conv = Conversation(title=title)
        now = _dt_iso(conv.created_at)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (%s, %s, %s, %s)",
                    (conv.id, conv.title, now, now),
                )
        return conv

    def get(self, conversation_id: str) -> Conversation | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, title, created_at, updated_at FROM conversations WHERE id = %s",
                    (conversation_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                cur.execute(
                    """
                    SELECT id, role, content, images_json, thinking,
                           tool_calls_json, sources_json, timestamp
                    FROM messages
                    WHERE conversation_id = %s
                    ORDER BY sort_order ASC, id ASC
                    """,
                    (conversation_id,),
                )
                msg_rows = cur.fetchall()
        messages = [_row_to_message(r) for r in msg_rows]
        return Conversation(
            id=row[0],
            title=row[1],
            messages=messages,
            created_at=_parse_dt(row[2]),
            updated_at=_parse_dt(row[3]),
        )

    def list_all(self) -> list[ConversationSummary]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT c.id, c.title, c.created_at, c.updated_at,
                           COUNT(m.id) AS message_count
                    FROM conversations c
                    LEFT JOIN messages m ON m.conversation_id = c.id
                    GROUP BY c.id
                    ORDER BY c.updated_at DESC
                """)
                rows = cur.fetchall()
        return [
            ConversationSummary(
                id=r[0],
                title=r[1],
                created_at=_parse_dt(r[2]),
                updated_at=_parse_dt(r[3]),
                message_count=int(r[4]),
            )
            for r in rows
        ]

    def rename(self, conversation_id: str, title: str) -> bool:
        now = _dt_iso(_utc_now())
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE conversations SET title = %s, updated_at = %s WHERE id = %s",
                    (title, now, conversation_id),
                )
                return cur.rowcount > 0

    def delete(self, conversation_id: str) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
                return cur.rowcount > 0

    def add_message(self, conversation_id: str, message: Message) -> None:
        images_json = json.dumps(message.images) if message.images else None
        thinking = message.thinking
        tool_calls_json = (
            json.dumps([tc.model_dump() for tc in message.tool_calls])
            if message.tool_calls
            else None
        )
        sources_json = (
            json.dumps([s.model_dump() for s in message.sources])
            if message.sources
            else None
        )
        ts = _dt_iso(message.timestamp)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM conversations WHERE id = %s", (conversation_id,)
                )
                if cur.fetchone() is None:
                    raise KeyError(f"Conversation {conversation_id} not found")
                cur.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) FROM messages WHERE conversation_id = %s",
                    (conversation_id,),
                )
                max_so = cur.fetchone()[0]
                sort_order = int(max_so) + 1
                cur.execute(
                    """
                    INSERT INTO messages (id, conversation_id, role, content, images_json,
                                          thinking, tool_calls_json, sources_json,
                                          timestamp, sort_order)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        message.id,
                        conversation_id,
                        message.role,
                        message.content,
                        images_json,
                        thinking,
                        tool_calls_json,
                        sources_json,
                        ts,
                        sort_order,
                    ),
                )
                now = _dt_iso(_utc_now())
                cur.execute(
                    "UPDATE conversations SET updated_at = %s WHERE id = %s",
                    (now, conversation_id),
                )
                if message.role == "user":
                    cur.execute(
                        "SELECT COUNT(*) FROM messages WHERE conversation_id = %s",
                        (conversation_id,),
                    )
                    count = cur.fetchone()[0]
                    if int(count) == 1:
                        title = message.content[:60].strip() or "New Chat"
                        cur.execute(
                            "UPDATE conversations SET title = %s WHERE id = %s",
                            (title, conversation_id),
                        )

    def get_messages(self, conversation_id: str) -> list[Message]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM conversations WHERE id = %s", (conversation_id,)
                )
                if cur.fetchone() is None:
                    raise KeyError(f"Conversation {conversation_id} not found")
                cur.execute(
                    """
                    SELECT id, role, content, images_json, thinking,
                           tool_calls_json, sources_json, timestamp
                    FROM messages
                    WHERE conversation_id = %s
                    ORDER BY sort_order ASC, id ASC
                    """,
                    (conversation_id,),
                )
                msg_rows = cur.fetchall()
        return [_row_to_message(r) for r in msg_rows]


def _row_to_message(row: tuple) -> Message:
    _id, role, content, images_json, thinking, tool_calls_json, sources_json, ts = (
        row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7],
    )
    images = json.loads(images_json) if images_json else None
    tool_calls = (
        [ToolCallRecord(**tc) for tc in json.loads(tool_calls_json)]
        if tool_calls_json
        else None
    )
    sources = (
        [Source(**s) for s in json.loads(sources_json)]
        if sources_json
        else None
    )
    return Message(
        id=_id,
        role=role,
        content=content,
        images=images,
        thinking=thinking or None,
        tool_calls=tool_calls,
        sources=sources,
        timestamp=_parse_dt(ts),
    )


store = ConversationStore()
