"""Caso de uso: consulta del registro de auditoría — Pilar III (Gobernanza
y Trazabilidad). Expone lo que ya se venía registrando desde la ronda de
Pilar II/III pero nunca se había podido consultar por API.

Solo ADMIN: el log agrega actividad de todos los usuarios.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from backend.application.ports.user_directory_port import UserDirectoryPort
from backend.core.exceptions import AuthorizationError
from backend.core.security.audit import AuditEvent, AuditLogger
from backend.core.security.identity import Principal
from backend.domain.user import Role, User

_ACTION_LABELS = {
    "login": "Inicio de sesión",
    "change_password": "Cambio de contraseña",
    "upload_document": "Subida de documento",
    "update_document": "Edición de documento",
    "delete_document": "Eliminación de documento",
    "query": "Consulta",
    "create_user": "Creación de usuario",
    "update_user": "Edición de usuario",
    "delete_user": "Eliminación de usuario",
}

_PERIOD_DELTAS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
}


@dataclass(frozen=True)
class AuditLogEntry:
    timestamp: datetime
    actor_name: str
    event_name: str
    context: str
    description: str
    success: bool


class GetAuditLogUseCase:
    def __init__(self, audit_logger: AuditLogger, user_directory: UserDirectoryPort):
        self._audit_logger = audit_logger
        self._user_directory = user_directory

    def execute(self, principal: Principal, period: Optional[str] = None) -> List[AuditLogEntry]:
        if Role.ADMIN.value not in principal.roles:
            raise AuthorizationError("Se requiere rol de administrador para ver los registros")

        since = datetime.now(timezone.utc) - _PERIOD_DELTAS[period] if period in _PERIOD_DELTAS else None
        events = self._audit_logger.list_events(since=since)
        users_by_id = {u.id: u for u in self._user_directory.list_users()}
        return [self._to_entry(event, users_by_id) for event in events]

    def _resolve_name(self, identifier: str, users_by_id: Dict[str, User]) -> str:
        user = users_by_id.get(identifier)
        return user.full_name if user else identifier

    def _to_entry(self, event: AuditEvent, users_by_id: Dict[str, User]) -> AuditLogEntry:
        is_user_action = event.action.endswith("_user")
        return AuditLogEntry(
            timestamp=event.timestamp,
            actor_name=self._resolve_name(event.actor, users_by_id),
            event_name=_ACTION_LABELS.get(event.action, event.action),
            context=self._resolve_name(event.resource, users_by_id) if is_user_action else event.resource,
            description=self._describe(event),
            success=event.success,
        )

    def _describe(self, event: AuditEvent) -> str:
        action = event.action
        details = event.details or {}

        if action == "login":
            return "Inicio de sesión exitoso" if event.success else "Intento de inicio de sesión fallido"
        if action == "change_password":
            return "Actualizó su contraseña"
        if action == "upload_document":
            if not event.success:
                return f"Falló la subida de \"{event.resource}\""
            chunks = details.get("chunk_count")
            suffix = f" ({chunks} fragmentos)" if chunks else ""
            return f"Subió el documento \"{event.resource}\"{suffix}"
        if action == "update_document":
            return f"Editó los metadatos de \"{event.resource}\""
        if action == "delete_document":
            return f"Eliminó el documento \"{event.resource}\""
        if action == "query":
            if details.get("result") == "no_evidence":
                return f"Preguntó \"{event.resource}\" (sin evidencia suficiente)"
            return f"Preguntó \"{event.resource}\""
        if action == "create_user":
            return f"Creó el usuario {details.get('email', event.resource)}"
        if action == "update_user":
            return "Editó los datos del usuario"
        if action == "delete_user":
            return "Eliminó al usuario"
        return "Evento del sistema"
