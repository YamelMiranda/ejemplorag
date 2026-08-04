"""Adapter de sesión basado en JWT (PyJWT, HS256)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from backend.core.exceptions import AuthenticationError
from backend.core.security.identity import Principal
from backend.core.security.tokens import TokenService


class JWTTokenService(TokenService):
    def __init__(self, secret_key: str, expire_minutes: int, algorithm: str = "HS256"):
        self._secret_key = secret_key
        self._expire_minutes = expire_minutes
        self._algorithm = algorithm

    def issue(self, principal: Principal) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": principal.id,
            "name": principal.display_name,
            "roles": principal.roles,
            "department": principal.department,
            "email": principal.email,
            "must_change_password": principal.must_change_password,
            "iat": now,
            "exp": now + timedelta(minutes=self._expire_minutes),
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def verify(self, token: str) -> Principal:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Sesión inválida o expirada, inicia sesión de nuevo") from exc

        return Principal(
            id=payload["sub"],
            display_name=payload.get("name", payload["sub"]),
            roles=payload.get("roles", []),
            department=payload.get("department"),
            email=payload.get("email"),
            must_change_password=payload.get("must_change_password", False),
        )
