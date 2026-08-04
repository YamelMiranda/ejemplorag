"""Adapter SQLite del directorio de usuarios (simula un Active Directory
propio — ver `backend.application.ports.user_directory_port`)."""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from backend.application.ports.user_directory_port import UserDirectoryPort
from backend.core.exceptions import ValidationError
from backend.core.security.passwords import hash_password, verify_password
from backend.domain.user import Role, User
from backend.infrastructure.persistence.sqlite.db import connect


def _row_to_user(row) -> User:
    return User(
        id=row["id"],
        email=row["email"],
        full_name=row["full_name"],
        department=row["department"],
        role=Role(row["role"]),
        is_active=bool(row["is_active"]),
        password_hash=row["password_hash"],
        must_change_password=bool(row["must_change_password"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        last_login_at=datetime.fromisoformat(row["last_login_at"]) if row["last_login_at"] else None,
    )


class SqliteUserDirectory(UserDirectoryPort):
    def __init__(self, db_path: Path):
        self._db_path = db_path

    def init(self) -> None:
        with connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    full_name TEXT NOT NULL,
                    department TEXT NOT NULL,
                    role TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    password_hash TEXT NOT NULL,
                    must_change_password INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    last_login_at TEXT
                )
                """
            )
            # Migración liviana para bases creadas antes de agregar esta
            # columna (sqlite no soporta "ADD COLUMN IF NOT EXISTS").
            try:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0"
                )
            except sqlite3.OperationalError:
                pass

    def count(self) -> int:
        with connect(self._db_path) as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
            return row["c"]

    def authenticate(self, email: str, password: str) -> Optional[User]:
        user = self.get_by_email(email)
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def get_by_id(self, user_id: str) -> Optional[User]:
        with connect(self._db_path) as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return _row_to_user(row) if row else None

    def get_by_email(self, email: str) -> Optional[User]:
        with connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
            ).fetchone()
            return _row_to_user(row) if row else None

    def list_users(self) -> List[User]:
        with connect(self._db_path) as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
            return [_row_to_user(row) for row in rows]

    def create_user(
        self, email: str, full_name: str, department: str, role: Role, password: str
    ) -> User:
        email = email.strip().lower()
        if self.get_by_email(email):
            raise ValidationError(f"Ya existe un usuario con el correo '{email}'")

        user = User(
            id=uuid.uuid4().hex,
            email=email,
            full_name=full_name,
            department=department,
            role=role,
            is_active=True,
            password_hash=hash_password(password),
            created_at=datetime.now(timezone.utc),
            last_login_at=None,
        )
        with connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO users
                    (id, email, full_name, department, role, is_active, password_hash,
                     must_change_password, created_at, last_login_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user.id,
                    user.email,
                    user.full_name,
                    user.department,
                    user.role.value,
                    1,
                    user.password_hash,
                    int(user.must_change_password),
                    user.created_at.isoformat(),
                    None,
                ),
            )
        return user

    def update_user(
        self,
        user_id: str,
        *,
        full_name: Optional[str] = None,
        department: Optional[str] = None,
        role: Optional[Role] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[User]:
        current = self.get_by_id(user_id)
        if not current:
            return None

        updated = current.model_copy(
            update={
                "full_name": full_name if full_name is not None else current.full_name,
                "department": department if department is not None else current.department,
                "role": role if role is not None else current.role,
                "is_active": is_active if is_active is not None else current.is_active,
            }
        )
        with connect(self._db_path) as conn:
            conn.execute(
                """
                UPDATE users
                SET full_name = ?, department = ?, role = ?, is_active = ?
                WHERE id = ?
                """,
                (updated.full_name, updated.department, updated.role.value, int(updated.is_active), user_id),
            )
        return updated

    def delete_user(self, user_id: str) -> bool:
        with connect(self._db_path) as conn:
            cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            return cursor.rowcount > 0

    def touch_last_login(self, user_id: str) -> None:
        with connect(self._db_path) as conn:
            conn.execute(
                "UPDATE users SET last_login_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), user_id),
            )

    def set_password(self, user_id: str, new_password: str, *, must_change_password: bool) -> None:
        with connect(self._db_path) as conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, must_change_password = ? WHERE id = ?",
                (hash_password(new_password), int(must_change_password), user_id),
            )
