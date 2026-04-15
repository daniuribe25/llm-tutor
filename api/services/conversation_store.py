from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from api.models.schemas import Conversation, ConversationSummary, Message


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _dt_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _default_db_path() -> Path:
    env = os.environ.get("CONVERSATION_DB")
    if env:
        return Path(env).expanduser()
    root = Path(__file__).resolve().parents[2]
    return root / "data" / "conversations.db"


class ConversationStore:
    """Thread-safe SQLite-backed conversation store."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else _default_db_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    images_json TEXT,
                    timestamp TEXT NOT NULL,
                    sort_order INTEGER NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                    ON messages (conversation_id, sort_order);
                """
            )

    def create(self, title: str = "New Chat") -> Conversation:
        conv = Conversation(title=title)
        now = _dt_iso(conv.created_at)
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (conv.id, conv.title, now, now),
            )
        return conv

    def get(self, conversation_id: str) -> Conversation | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
            if row is None:
                return None
            msg_rows = conn.execute(
                """
                SELECT id, role, content, images_json, timestamp
                FROM messages
                WHERE conversation_id = ?
                ORDER BY sort_order ASC, id ASC
                """,
                (conversation_id,),
            ).fetchall()
        messages = [_row_to_message(r) for r in msg_rows]
        return Conversation(
            id=row[0],
            title=row[1],
            messages=messages,
            created_at=_parse_dt(row[2]),
            updated_at=_parse_dt(row[3]),
        )

    def list_all(self) -> list[ConversationSummary]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT c.id, c.title, c.created_at, c.updated_at,
                       COUNT(m.id) AS message_count
                FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.id
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                """
            ).fetchall()
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

    def delete(self, conversation_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            return cur.rowcount > 0

    def add_message(self, conversation_id: str, message: Message) -> None:
        images_json = json.dumps(message.images) if message.images else None
        ts = _dt_iso(message.timestamp)
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"Conversation {conversation_id} not found")
            max_so = conn.execute(
                "SELECT COALESCE(MAX(sort_order), -1) FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()[0]
            sort_order = int(max_so) + 1
            conn.execute(
                """
                INSERT INTO messages (id, conversation_id, role, content, images_json, timestamp, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    conversation_id,
                    message.role,
                    message.content,
                    images_json,
                    ts,
                    sort_order,
                ),
            )
            now = _dt_iso(_utc_now())
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
            if message.role == "user":
                count = conn.execute(
                    "SELECT COUNT(*) FROM messages WHERE conversation_id = ?",
                    (conversation_id,),
                ).fetchone()[0]
                if int(count) == 1:
                    title = message.content[:60].strip() or "New Chat"
                    conn.execute(
                        "UPDATE conversations SET title = ? WHERE id = ?",
                        (title, conversation_id),
                    )
            conn.commit()

    def get_messages(self, conversation_id: str) -> list[Message]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"Conversation {conversation_id} not found")
            msg_rows = conn.execute(
                """
                SELECT id, role, content, images_json, timestamp
                FROM messages
                WHERE conversation_id = ?
                ORDER BY sort_order ASC, id ASC
                """,
                (conversation_id,),
            ).fetchall()
        return [_row_to_message(r) for r in msg_rows]


def _row_to_message(row: tuple) -> Message:
    _id, role, content, images_json, ts = row[0], row[1], row[2], row[3], row[4]
    images = json.loads(images_json) if images_json else None
    return Message(
        id=_id,
        role=role,
        content=content,
        images=images,
        timestamp=_parse_dt(ts),
    )


store = ConversationStore()
