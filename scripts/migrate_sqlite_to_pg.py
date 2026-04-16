"""One-shot migration: SQLite (data/conversations.db) → PostgreSQL (DATABASE_URL)."""

import os
import sqlite3
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

SQLITE_PATH = ROOT / "data" / "conversations.db"
DATABASE_URL = os.environ.get("DATABASE_URL")


def main() -> None:
    if not SQLITE_PATH.exists():
        print(f"SQLite DB not found at {SQLITE_PATH}")
        return
    if not DATABASE_URL:
        print("DATABASE_URL not set — check your .env")
        return

    lite = sqlite3.connect(SQLITE_PATH)
    pg = psycopg2.connect(DATABASE_URL)

    try:
        cur_pg = pg.cursor()

        # --- conversations ---
        rows = lite.execute(
            "SELECT id, title, created_at, updated_at FROM conversations"
        ).fetchall()
        print(f"Migrating {len(rows)} conversations...")
        for r in rows:
            cur_pg.execute(
                """INSERT INTO conversations (id, title, created_at, updated_at)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (id) DO NOTHING""",
                r,
            )

        # --- messages ---
        rows = lite.execute(
            """SELECT id, conversation_id, role, content, images_json,
                      thinking, tool_calls_json, sources_json,
                      timestamp, sort_order
               FROM messages
               ORDER BY sort_order ASC"""
        ).fetchall()
        print(f"Migrating {len(rows)} messages...")
        for r in rows:
            cur_pg.execute(
                """INSERT INTO messages
                       (id, conversation_id, role, content, images_json,
                        thinking, tool_calls_json, sources_json,
                        timestamp, sort_order)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO NOTHING""",
                r,
            )

        pg.commit()
        print("Done — all data migrated successfully.")

    except Exception:
        pg.rollback()
        raise
    finally:
        lite.close()
        pg.close()


if __name__ == "__main__":
    main()
