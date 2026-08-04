"""Caso de uso: gestión del directorio de usuarios — Pilar II.

A diferencia del resto de casos de uso (que dependen de `AccessPolicy`, hoy
permisivo porque el RBAC de documentos todavía no está implementado), la
gestión de usuarios exige rol ADMIN de forma directa: es la única
superficie que ya tiene control de acceso real en esta etapa del proyecto
(ver SECURITY_ROADMAP.md).
"""
from __future__ import annotations

from typing import List, Optional

from backend.application.ports.user_directory_port import UserDirectoryPort
from backend.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from backend.core.security.audit import AuditEvent, AuditLogger
from backend.core.security.identity import Principal
from backend.domain.user import Role, User


class ManageUsersUseCase:
    def __init__(self, user_directory: UserDirectoryPort, audit_logger: AuditLogger):
        self._user_directory = user_directory
        self._audit_logger = audit_logger

    def _require_admin(self, principal: Principal) -> None:
        if Role.ADMIN.value not in principal.roles:
            raise AuthorizationError("Se requiere rol de administrador para gestionar usuarios")

    def list_users(self, principal: Principal) -> List[User]:
        self._require_admin(principal)
        return self._user_directory.list_users()

    def create_user(
        self,
        principal: Principal,
        email: str,
        full_name: str,
        department: str,
        role: Role,
        password: str,
    ) -> User:
        self._require_admin(principal)
        if not password or len(password) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres")

        user = self._user_directory.create_user(email, full_name, department, role, password)
        self._audit_logger.record(
            AuditEvent(
                actor=principal.id,
                action="create_user",
                resource=user.id,
                success=True,
                details={"email": user.email, "role": user.role.value},
            )
        )
        return user

    def update_user(
        self,
        principal: Principal,
        user_id: str,
        *,
        full_name: Optional[str] = None,
        department: Optional[str] = None,
        role: Optional[Role] = None,
        is_active: Optional[bool] = None,
    ) -> User:
        self._require_admin(principal)
        updated = self._user_directory.update_user(
            user_id, full_name=full_name, department=department, role=role, is_active=is_active
        )
        if not updated:
            raise NotFoundError(f"Usuario '{user_id}' no encontrado")

        self._audit_logger.record(
            AuditEvent(actor=principal.id, action="update_user", resource=user_id, success=True)
        )
        return updated

    def delete_user(self, principal: Principal, user_id: str) -> None:
        self._require_admin(principal)
        if principal.id == user_id:
            raise ValidationError("No puedes eliminar tu propia cuenta")

        deleted = self._user_directory.delete_user(user_id)
        if not deleted:
            raise NotFoundError(f"Usuario '{user_id}' no encontrado")

        self._audit_logger.record(
            AuditEvent(actor=principal.id, action="delete_user", resource=user_id, success=True)
        )
