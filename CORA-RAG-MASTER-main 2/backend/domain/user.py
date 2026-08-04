"""Entidades de dominio del directorio de usuarios — Pilar II (Gestión de
Identidades y Accesos).

Hoy el directorio vive en nuestra propia base (ver
`backend.infrastructure.persistence.sqlite.user_repository`), simulando lo
que sería un Active Directory/LDAP real. Está modelado detrás de
`UserDirectoryPort` justamente para que conectar un LDAP real más adelante
sea agregar un adapter nuevo, no rediseñar el dominio.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Role(str, Enum):
    EMPLOYEE = "EMPLOYEE"
    SUPERVISOR = "SUPERVISOR"
    ADMIN = "ADMIN"


class User(BaseModel):
    """Un usuario del directorio. `password_hash` nunca sale de la capa de
    infraestructura/aplicación hacia la API — los DTOs de respuesta lo
    excluyen explícitamente."""

    id: str
    email: str
    full_name: str
    department: str
    role: Role
    is_active: bool = True
    password_hash: str
    # Reinicio forzado de contraseña (Pilar II): true para toda cuenta
    # creada por un admin desde el panel — el admin le da una contraseña
    # simple/temporal, y el usuario debe reemplazarla en su primer login
    # antes de poder usar el resto de la app.
    must_change_password: bool = True
    created_at: datetime
    last_login_at: Optional[datetime] = None
