"""Caso de uso: ingesta de un documento subido al Repositorio de Conocimiento.

Orquesta: autorizar -> guardar en disco -> resolver document_id/versión ->
cargar y trocear -> calcular metadatos estándar -> generar embeddings ->
persistir en el vector store -> registrar en el índice de documentos ->
auditar (Pilar I: integridad vía document_hash; Pilar III: auditoría).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.application.ports.document_loader_port import DocumentLoaderPort
from backend.application.ports.document_registry_port import (
    DocumentRegistryPort,
    RegisteredDocument,
)
from backend.application.ports.document_storage_port import DocumentStoragePort
from backend.application.ports.embedding_port import EmbeddingPort
from backend.application.ports.vector_store_port import VectorStorePort
from backend.core.exceptions import AuthorizationError, IngestionError, ValidationError
from backend.core.security.audit import AuditEvent, AuditLogger
from backend.core.security.authorization import AccessPolicy, Action
from backend.core.security.identity import Principal
from backend.domain.document import (
    Chunk,
    DocumentMetadata,
    build_chunk_id,
    classification_for,
    compute_document_hash,
    new_document_id,
)
from backend.domain.user import Role


@dataclass(frozen=True)
class IngestResult:
    document_id: str
    document_version: int
    source_file: str
    chunk_count: int


class IngestDocumentUseCase:
    def __init__(
        self,
        document_storage: DocumentStoragePort,
        document_registry: DocumentRegistryPort,
        document_loader: DocumentLoaderPort,
        embedder: EmbeddingPort,
        vector_store: VectorStorePort,
        access_policy: AccessPolicy,
        audit_logger: AuditLogger,
        chunk_size: int,
        chunk_overlap: int,
    ):
        self._document_storage = document_storage
        self._document_registry = document_registry
        self._document_loader = document_loader
        self._embedder = embedder
        self._vector_store = vector_store
        self._access_policy = access_policy
        self._audit_logger = audit_logger
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def execute(
        self,
        principal: Principal,
        filename: str,
        content: bytes,
        *,
        department: str,
        visible_department: Optional[str] = None,
        minimum_role: Role = Role.EMPLOYEE,
    ) -> IngestResult:
        if not department or not department.strip():
            raise ValidationError(
                "El departamento del documento es obligatorio: no se pudo inferir "
                "automáticamente, así que debe indicarse al subirlo."
            )

        if not self._access_policy.can(principal, Action.UPLOAD_DOCUMENT, filename):
            self._audit_logger.record(
                AuditEvent(
                    actor=principal.id,
                    action=Action.UPLOAD_DOCUMENT.value,
                    resource=filename,
                    success=False,
                )
            )
            raise AuthorizationError(f"'{principal.id}' no está autorizado a subir documentos")

        saved_path = self._document_storage.save(filename, content)

        try:
            result = self._ingest_saved_file(
                principal,
                saved_path,
                content,
                department=department.strip(),
                visible_department=visible_department,
                minimum_role=minimum_role,
            )
        except Exception as exc:
            self._audit_logger.record(
                AuditEvent(
                    actor=principal.id,
                    action=Action.UPLOAD_DOCUMENT.value,
                    resource=filename,
                    success=False,
                    details={"error": str(exc)},
                )
            )
            raise

        self._audit_logger.record(
            AuditEvent(
                actor=principal.id,
                action=Action.UPLOAD_DOCUMENT.value,
                resource=filename,
                success=True,
                details={
                    "document_id": result.document_id,
                    "document_version": result.document_version,
                    "chunk_count": result.chunk_count,
                },
            )
        )
        return result

    def _ingest_saved_file(
        self,
        principal: Principal,
        saved_path: Path,
        content: bytes,
        *,
        department: str,
        visible_department: Optional[str],
        minimum_role: Role,
    ) -> IngestResult:
        source_file = saved_path.name
        document_hash = compute_document_hash(content)
        now = datetime.now(timezone.utc)

        existing = self._document_registry.get_by_source_file(source_file)
        if existing:
            document_id = existing.document_id
            document_version = existing.current_version + 1
            upload_timestamp = existing.upload_timestamp
            # una nueva versión reemplaza el contexto recuperable de la anterior
            self._vector_store.delete_by_source(source_file)
        else:
            document_id = new_document_id()
            document_version = 1
            upload_timestamp = now

        raw_chunks = self._document_loader.load_and_split(
            saved_path, self._chunk_size, self._chunk_overlap
        )
        if not raw_chunks:
            raise IngestionError(f"El archivo '{source_file}' no produjo contenido indexable")

        chunks = [
            Chunk(
                content=raw_chunk.content,
                metadata=DocumentMetadata(
                    document_id=document_id,
                    document_version=document_version,
                    classification=classification_for(minimum_role),
                    department=department,
                    owner=principal.id,
                    visible_department=visible_department,
                    minimum_role=minimum_role,
                    uploaded_by=principal.id,
                    upload_timestamp=upload_timestamp,
                    last_modified=now,
                    document_hash=document_hash,
                    chunk_id=build_chunk_id(document_id, document_version, index),
                    chunk_index=index,
                    content_length=len(raw_chunk.content),
                    embedding_model=self._embedder.model_name,
                    source_file=source_file,
                    file_type=raw_chunk.file_type,
                    page=raw_chunk.page,
                ),
            )
            for index, raw_chunk in enumerate(raw_chunks)
        ]

        embeddings = self._embedder.embed([chunk.content for chunk in chunks])
        self._vector_store.add_chunks(chunks, embeddings)

        self._document_registry.upsert(
            RegisteredDocument(
                document_id=document_id,
                source_file=source_file,
                current_version=document_version,
                document_hash=document_hash,
                uploaded_by=principal.id,
                upload_timestamp=upload_timestamp,
                last_modified=now,
            )
        )

        return IngestResult(
            document_id=document_id,
            document_version=document_version,
            source_file=source_file,
            chunk_count=len(chunks),
        )
