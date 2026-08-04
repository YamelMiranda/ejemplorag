"""Adapter SQLite para el registro de documentos (document_id/versión estables)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from backend.application.ports.document_registry_port import (
    DocumentRegistryPort,
    RegisteredDocument,
)
from backend.infrastructure.persistence.sqlite.db import connect


def _row_to_entry(row) -> RegisteredDocument:
    return RegisteredDocument(
        document_id=row["document_id"],
        source_file=row["source_file"],
        current_version=row["current_version"],
        document_hash=row["document_hash"],
        uploaded_by=row["uploaded_by"],
        upload_timestamp=datetime.fromisoformat(row["upload_timestamp"]),
        last_modified=datetime.fromisoformat(row["last_modified"]),
    )


class SqliteDocumentRegistry(DocumentRegistryPort):
    def __init__(self, db_path: Path):
        self._db_path = db_path

    def init(self) -> None:
        with connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents_registry (
                    source_file TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    current_version INTEGER NOT NULL,
                    document_hash TEXT NOT NULL,
                    uploaded_by TEXT NOT NULL,
                    upload_timestamp TEXT NOT NULL,
                    last_modified TEXT NOT NULL
                )
                """
            )

    def get_by_source_file(self, source_file: str) -> Optional[RegisteredDocument]:
        with connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM documents_registry WHERE source_file = ?", (source_file,)
            ).fetchone()
            return _row_to_entry(row) if row else None

    def upsert(self, entry: RegisteredDocument) -> None:
        with connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO documents_registry
                    (source_file, document_id, current_version, document_hash,
                     uploaded_by, upload_timestamp, last_modified)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_file) DO UPDATE SET
                    current_version = excluded.current_version,
                    document_hash = excluded.document_hash,
                    uploaded_by = excluded.uploaded_by,
                    last_modified = excluded.last_modified
                """,
                (
                    entry.source_file,
                    entry.document_id,
                    entry.current_version,
                    entry.document_hash,
                    entry.uploaded_by,
                    entry.upload_timestamp.isoformat(),
                    entry.last_modified.isoformat(),
                ),
            )

    def delete(self, source_file: str) -> None:
        with connect(self._db_path) as conn:
            conn.execute("DELETE FROM documents_registry WHERE source_file = ?", (source_file,))

    def list_all(self) -> List[RegisteredDocument]:
        with connect(self._db_path) as conn:
            rows = conn.execute("SELECT * FROM documents_registry").fetchall()
        return [_row_to_entry(row) for row in rows]
