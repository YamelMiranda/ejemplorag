"""Puerto de registro de documentos.

Mapea cada archivo fuente a un `document_id` estable y a la versión vigente,
independientemente de ChromaDB. Es lo que permite que re-subir un archivo
con el mismo nombre incremente `document_version` en vez de crear una
identidad nueva — base para el versionado documental (Pilar I / Pilar III).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class RegisteredDocument:
    document_id: str
    source_file: str
    current_version: int
    document_hash: str
    uploaded_by: str
    upload_timestamp: datetime
    last_modified: datetime


class DocumentRegistryPort(ABC):
    @abstractmethod
    def init(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_by_source_file(self, source_file: str) -> Optional[RegisteredDocument]:
        raise NotImplementedError

    @abstractmethod
    def upsert(self, entry: RegisteredDocument) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, source_file: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> List[RegisteredDocument]:
        raise NotImplementedError
