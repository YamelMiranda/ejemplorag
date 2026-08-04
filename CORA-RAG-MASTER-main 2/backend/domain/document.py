"""Entidades de dominio del Repositorio de Conocimiento Empresarial de CORA.

ChromaDB no se trata como un vector store genérico: cada chunk persiste el
estándar de metadatos completo definido en `DocumentMetadata` (16 campos),
de modo que clasificación, propiedad, versión y control de acceso
documental sean de primera clase desde ya — aunque RBAC/AD todavía no los
hagan cumplir (ver SECURITY_ROADMAP.md, Pilar I).
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from backend.domain.user import Role


class Classification(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


def classification_for(minimum_role: Role) -> Classification:
    """`classification` se deriva de `minimum_role` en vez de pedirse en el
    formulario de subida — el usuario ya expresa la sensibilidad del
    documento eligiendo quién lo puede ver; no tiene sentido pedírselo dos
    veces con dos vocabularios distintos."""
    if minimum_role == Role.ADMIN:
        return Classification.RESTRICTED
    if minimum_role == Role.SUPERVISOR:
        return Classification.CONFIDENTIAL
    return Classification.INTERNAL


class FileType(str, Enum):
    PDF = "pdf"
    TXT = "txt"
    HTML = "html"


def compute_document_hash(content: bytes) -> str:
    """Hash de integridad del contenido original (Pilar I)."""
    return hashlib.sha256(content).hexdigest()


def new_document_id() -> str:
    return uuid.uuid4().hex


def build_chunk_id(document_id: str, document_version: int, chunk_index: int) -> str:
    """El chunk_id incluye la versión del documento para poder conservar
    versiones anteriores en el Repositorio de Conocimiento en vez de
    pisarlas (versionado documental, ver SECURITY_ROADMAP.md)."""
    return f"{document_id}_v{document_version}_{chunk_index}"


class DocumentMetadata(BaseModel):
    """Estándar de metadatos aplicado a cada chunk almacenado en el
    Repositorio de Conocimiento."""

    document_id: str
    document_version: int = 1
    classification: Classification = Classification.INTERNAL
    department: str = "general"
    owner: str = "system"
    # RBAC real (ver backend/core/security/authorization.py:
    # can_view_document). `visible_department=None` significa "toda la
    # empresa"; `minimum_role` es jerárquico (EMPLOYEE ⊆ SUPERVISOR ⊆
    # ADMIN) — un rol superior siempre ve lo que ve uno inferior.
    visible_department: Optional[str] = None
    minimum_role: Role = Role.EMPLOYEE
    uploaded_by: str = "system"
    upload_timestamp: datetime
    last_modified: datetime
    document_hash: str
    chunk_id: str
    chunk_index: int
    content_length: int
    embedding_model: str
    source_file: str
    file_type: FileType

    # Campo adicional (fuera del estándar de 16) que preserva el número de
    # página cuando el origen es un PDF, usado solo para citar la fuente en
    # las referencias del chat — no reemplaza ningún campo del estándar.
    page: Optional[int] = None

    def to_chroma_metadata(self) -> dict:
        """Aplana el modelo a los tipos primitivos que acepta ChromaDB.

        ChromaDB no admite `None` como valor de metadata, así que los
        campos opcionales ausentes (p. ej. `page` en archivos que no son
        PDF) se omiten en vez de enviarse como null.
        """
        data = self.model_dump(mode="json")
        return {key: value for key, value in data.items() if value is not None}


class Chunk(BaseModel):
    """Un fragmento de documento, listo para ser embebido e indexado."""

    content: str
    metadata: DocumentMetadata
