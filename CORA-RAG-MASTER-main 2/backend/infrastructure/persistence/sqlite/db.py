"""Utilidad de conexión SQLite compartida por los repositorios de infraestructura."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
