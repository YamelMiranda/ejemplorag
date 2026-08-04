"""Adapter SQLite para el registro de auditoría — Pilar III (Gobernanza y
Trazabilidad). Vive en un archivo de base de datos separado del historial de
chats (`settings.audit_db_path`) para mantener la pista de auditoría aislada
del resto del estado operativo.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from backend.core.security.audit import AuditEvent, AuditLogger
from backend.infrastructure.persistence.sqlite.db import connect


class SqliteAuditLogger(AuditLogger):
    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._init()

    def _init(self) -> None:
        with connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    details TEXT,
                    timestamp TEXT NOT NULL
                )
                """
            )

    def record(self, event: AuditEvent) -> None:
        with connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO audit_log (actor, action, resource, success, details, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    event.actor,
                    event.action,
                    event.resource,
                    1 if event.success else 0,
                    json.dumps(event.details),
                    event.timestamp.isoformat(),
                ),
            )

    def list_events(self, since: Optional[datetime] = None) -> List[AuditEvent]:
        query = "SELECT * FROM audit_log"
        params: tuple = ()
        if since is not None:
            query += " WHERE timestamp >= ?"
            params = (since.isoformat(),)
        query += " ORDER BY timestamp DESC"

        with connect(self._db_path) as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            AuditEvent(
                actor=row["actor"],
                action=row["action"],
                resource=row["resource"],
                success=bool(row["success"]),
                details=json.loads(row["details"]) if row["details"] else {},
                timestamp=datetime.fromisoformat(row["timestamp"]),
            )
            for row in rows
        ]
