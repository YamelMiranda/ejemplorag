"""Adapter SQLite para el historial de chats de CORA."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from backend.application.ports.chat_repository_port import ChatRepositoryPort
from backend.domain.chat import Chat, DocumentReference, Message, MessageRole
from backend.infrastructure.persistence.sqlite.db import connect


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteChatRepository(ChatRepositoryPort):
    def __init__(self, db_path: Path):
        self._db_path = db_path

    def init(self) -> None:
        with connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(chat_id) REFERENCES chats(id)
                )
                """
            )

    def create_chat(self, title: str) -> str:
        chat_id = str(uuid.uuid4())
        now = _now()
        with connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO chats (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (chat_id, title[:80], now, now),
            )
        return chat_id

    def chat_exists(self, chat_id: str) -> bool:
        with connect(self._db_path) as conn:
            row = conn.execute("SELECT 1 FROM chats WHERE id = ?", (chat_id,)).fetchone()
            return row is not None

    def add_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        sources: Optional[List[DocumentReference]] = None,
    ) -> str:
        msg_id = str(uuid.uuid4())
        now = _now()
        sources_json = json.dumps([s.model_dump(mode="json") for s in (sources or [])])
        with connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO messages (id, chat_id, role, content, sources, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (msg_id, chat_id, role, content, sources_json, now),
            )
            conn.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now, chat_id))
        return msg_id

    def list_chats(self) -> List[dict]:
        with connect(self._db_path) as conn:
            rows = conn.execute(
                """
                SELECT c.id, c.title, c.created_at, c.updated_at,
                       COUNT(m.id) AS message_count
                FROM chats c
                LEFT JOIN messages m ON m.chat_id = c.id
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def get_chat(self, chat_id: str) -> Optional[Chat]:
        with connect(self._db_path) as conn:
            chat_row = conn.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
            if not chat_row:
                return None
            message_rows = conn.execute(
                "SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at ASC",
                (chat_id,),
            ).fetchall()

        messages = [
            Message(
                id=row["id"],
                chat_id=row["chat_id"],
                role=MessageRole(row["role"]),
                content=row["content"],
                sources=[DocumentReference(**s) for s in json.loads(row["sources"] or "[]")],
                created_at=row["created_at"],
            )
            for row in message_rows
        ]
        return Chat(
            id=chat_row["id"],
            title=chat_row["title"],
            created_at=chat_row["created_at"],
            updated_at=chat_row["updated_at"],
            messages=messages,
        )

    def delete_chat(self, chat_id: str) -> None:
        with connect(self._db_path) as conn:
            conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
            conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))

    def count_chats(self) -> int:
        with connect(self._db_path) as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM chats").fetchone()
            return row["c"]

    def count_user_messages(self) -> int:
        with connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM messages WHERE role = 'user'"
            ).fetchone()
            return row["c"]
