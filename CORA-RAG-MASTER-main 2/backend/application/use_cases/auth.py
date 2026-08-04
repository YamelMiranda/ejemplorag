"""Casos de uso de autenticación — Pilar II (Gestión de Identidades y
Accesos): inicio de sesión y cambio de contraseña (incluyendo el reinicio
forzado del primer login)."""
from __future__ import annotations

from dataclasses import dataclass, replace

from backend.application.ports.user_directory_port import UserDirectoryPort
from backend.core.exceptions import AuthenticationError, ValidationError
from backend.core.security.audit import AuditEvent, AuditLogger
from backend.core.security.identity import Principal
from backend.core.security.passwords import verify_password
from backend.core.security.tokens import TokenService


@dataclass(frozen=True)
class LoginResult:
    token: str
    principal: Principal


def _principal_for(user) -> Principal:
    return Principal(
        id=user.id,
        display_name=user.full_name,
        roles=[user.role.value],
        department=user.department,
        email=user.email,
        must_change_password=user.must_change_password,
    )


class LoginUseCase:
    def __init__(
        self,
        user_directory: UserDirectoryPort,
        token_service: TokenService,
        audit_logger: AuditLogger,
    ):
        self._user_directory = user_directory
        self._token_service = token_service
        self._audit_logger = audit_logger

    def execute(self, email: str, password: str) -> LoginResult:
        user = self._user_directory.authenticate(email, password)
        if not user:
            self._audit_logger.record(
                AuditEvent(actor=email, action="login", resource="auth", success=False)
            )
            raise AuthenticationError("Correo o contraseña incorrectos")

        principal = _principal_for(user)
        token = self._token_service.issue(principal)
        self._user_directory.touch_last_login(user.id)

        self._audit_logger.record(
            AuditEvent(actor=user.id, action="login", resource="auth", success=True)
        )
        return LoginResult(token=token, principal=principal)


class ChangePasswordUseCase:
    """Cambio de contraseña por el propio usuario — cubre tanto el cambio
    voluntario (desde "Tu cuenta") como el reinicio forzado del primer
    login (`Principal.must_change_password`)."""

    def __init__(
        self,
        user_directory: UserDirectoryPort,
        token_service: TokenService,
        audit_logger: AuditLogger,
    ):
        self._user_directory = user_directory
        self._token_service = token_service
        self._audit_logger = audit_logger

    def execute(self, principal: Principal, current_password: str, new_password: str) -> LoginResult:
        user = self._user_directory.get_by_id(principal.id)
        if not user:
            raise AuthenticationError("Sesión inválida, inicia sesión de nuevo")

        if not verify_password(current_password, user.password_hash):
            self._audit_logger.record(
                AuditEvent(actor=principal.id, action="change_password", resource="auth", success=False)
            )
            raise AuthenticationError("La contraseña actual no es correcta")

        if len(new_password) < 8:
            raise ValidationError("La nueva contraseña debe tener al menos 8 caracteres")

        self._user_directory.set_password(user.id, new_password, must_change_password=False)

        updated_principal = replace(principal, must_change_password=False)
        token = self._token_service.issue(updated_principal)

        self._audit_logger.record(
            AuditEvent(actor=principal.id, action="change_password", resource="auth", success=True)
        )
        return LoginResult(token=token, principal=updated_principal)
