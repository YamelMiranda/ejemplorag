"""Puerto de emisión/verificación de tokens de sesión — Pilar II.

Hoy el único adapter es JWT
(`backend.infrastructure.security.jwt_token_service.JWTTokenService`).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from backend.core.security.identity import Principal


class TokenService(ABC):
    @abstractmethod
    def issue(self, principal: Principal) -> str:
        raise NotImplementedError

    @abstractmethod
    def verify(self, token: str) -> Principal:
        """Debe lanzar `backend.core.exceptions.AuthenticationError` si el
        token falta, expiró o fue manipulado."""
        raise NotImplementedError
