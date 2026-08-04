"""Caso de uso: gestión de documentos ya cargados en el Repositorio de
Conocimiento (listar y eliminar)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.application.ports.document_registry_port import DocumentRegistryPort
from backend.application.ports.document_storage_port import DocumentStoragePort
from backend.application.ports.vector_store_port import VectorStorePort
from backend.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from backend.core.security.audit import AuditEvent, AuditLogger
from backend.core.security.authorization import AccessPolicy, Action, can_view_document
from backend.core.security.identity import Principal
from backend.domain.document import classification_for
from backend.domain.user import Role


@dataclass(frozen=True)
class DocumentSummary:
    name: str
    file_type: str
    size_bytes: int
    uploaded_at: str
    document_version: int
    chunks: int
    estado: str
    # Estándar de metadatos del Repositorio de Conocimiento (solo
    # disponibles una vez que el documento quedó indexado, es decir,
    # `estado == "Listo"`).
    document_id: Optional[str] = None
    classification: Optional[str] = None
    department: Optional[str] = None
    owner: Optional[str] = None
    visible_department: Optional[str] = None
    minimum_role: Optional[str] = None
    uploaded_by: Optional[str] = None
    document_hash: Optional[str] = None
    embedding_model: Optional[str] = None


class ManageDocumentsUseCase:
    def __init__(
        self,
        document_storage: DocumentStoragePort,
        document_registry: DocumentRegistryPort,
        vector_store: VectorStorePort,
        access_policy: AccessPolicy,
        audit_logger: AuditLogger,
    ):
        self._document_storage = document_storage
        self._document_registry = document_registry
        self._vector_store = vector_store
        self._access_policy = access_policy
        self._audit_logger = audit_logger

    def list_documents(self, principal: Principal) -> List[DocumentSummary]:
        if not self._access_policy.can(principal, Action.READ_DOCUMENT, "*"):
            raise AuthorizationError(f"'{principal.id}' no está autorizado a listar documentos")

        indexed = self._vector_store.list_source_files()
        registry_by_name = {entry.source_file: entry for entry in self._document_registry.list_all()}

        summaries: List[DocumentSummary] = []
        for file_path in self._document_storage.list_files():
            stat = file_path.stat()
            chunk_info = indexed.get(file_path.name)
            registry_entry = registry_by_name.get(file_path.name)
            sample_metadata = chunk_info.get("metadata", {}) if chunk_info else {}

            # RBAC real (Pilar IV): un documento ya indexado y restringido a
            # otro departamento/rol ni siquiera aparece en el listado de
            # quien no puede verlo. Mientras no hay metadata (documento
            # recién subido, todavía "Procesando") se muestra igual: no hay
            # restricción que aplicar todavía.
            if sample_metadata and not can_view_document(
                principal,
                sample_metadata.get("visible_department"),
                sample_metadata.get("minimum_role", Role.EMPLOYEE.value),
            ):
                continue

            summaries.append(
                DocumentSummary(
                    name=file_path.name,
                    file_type=file_path.suffix.lstrip(".").lower(),
                    size_bytes=stat.st_size,
                    uploaded_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    document_version=registry_entry.current_version if registry_entry else 1,
                    chunks=chunk_info["chunks"] if chunk_info else 0,
                    estado="Listo" if chunk_info else "Procesando",
                    document_id=sample_metadata.get("document_id"),
                    classification=sample_metadata.get("classification"),
                    department=sample_metadata.get("department"),
                    owner=sample_metadata.get("owner"),
                    visible_department=sample_metadata.get("visible_department"),
                    minimum_role=sample_metadata.get("minimum_role"),
                    uploaded_by=sample_metadata.get("uploaded_by"),
                    document_hash=sample_metadata.get("document_hash"),
                    embedding_model=sample_metadata.get("embedding_model"),
                )
            )
        summaries.sort(key=lambda d: d.uploaded_at, reverse=True)
        return summaries

    def total_documents(self, principal: Principal) -> int:
        return len(self.list_documents(principal))

    def delete_document(self, principal: Principal, filename: str) -> None:
        if not self._access_policy.can(principal, Action.DELETE_DOCUMENT, filename):
            self._audit_logger.record(
                AuditEvent(
                    actor=principal.id,
                    action=Action.DELETE_DOCUMENT.value,
                    resource=filename,
                    success=False,
                )
            )
            raise AuthorizationError(f"'{principal.id}' no está autorizado a eliminar documentos")

        resolved_name = self._document_storage.delete(filename)
        if not resolved_name:
            raise NotFoundError(f"Documento '{filename}' no encontrado")

        self._vector_store.delete_by_source(resolved_name)
        self._document_registry.delete(resolved_name)

        self._audit_logger.record(
            AuditEvent(
                actor=principal.id,
                action=Action.DELETE_DOCUMENT.value,
                resource=resolved_name,
                success=True,
            )
        )

    def update_document(
        self,
        principal: Principal,
        filename: str,
        *,
        department: str,
        visible_department: Optional[str],
        minimum_role: Role,
    ) -> None:
        """Edita metadatos de un documento ya indexado (departamento
        dueño, departamento visible, rol mínimo) sin volver a subir el
        archivo ni regenerar embeddings. Reemplaza el estado completo de
        estos campos (no es un patch parcial) — el formulario de edición
        siempre reenvía los tres juntos."""
        if not self._access_policy.can(principal, Action.UPDATE_DOCUMENT, filename):
            self._audit_logger.record(
                AuditEvent(
                    actor=principal.id,
                    action=Action.UPDATE_DOCUMENT.value,
                    resource=filename,
                    success=False,
                )
            )
            raise AuthorizationError(f"'{principal.id}' no está autorizado a editar documentos")

        if not department or not department.strip():
            raise ValidationError("El departamento del documento no puede quedar vacío")

        matches = [doc for doc in self._document_storage.list_files() if doc.name == filename]
        if not matches:
            raise NotFoundError(f"Documento '{filename}' no encontrado")

        updates: Dict[str, Any] = {
            "department": department.strip(),
            "visible_department": visible_department,
            "minimum_role": minimum_role.value,
            "classification": classification_for(minimum_role).value,
        }
        self._vector_store.update_document_metadata(filename, updates)

        self._audit_logger.record(
            AuditEvent(
                actor=principal.id,
                action=Action.UPDATE_DOCUMENT.value,
                resource=filename,
                success=True,
                details=updates,
            )
        )
