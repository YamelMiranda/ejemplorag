"""Identidad del solicitante — Pilar II (Gestión de Identidades y Accesos).

`Principal` es la identidad autenticada que fluye por toda la aplicación:
los casos de uso solo conocen este tipo, nunca cookies, JWT ni el
directorio de usuarios concreto. La resolución real de "quién hace esta
request" (leer la cookie de sesión, verificar el JWT) vive en
`backend.api.dependencies.get_current_principal` — es responsabilidad de la
capa API, no de `core`, para no acoplar este módulo a FastAPI ni a la
inyección de dependencias concreta.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class Principal:
    """Identidad autenticada."""

    id: str
    display_name: str
    roles: List[str] = field(default_factory=list)
    department: Optional[str] = None
    email: Optional[str] = None
    must_change_password: bool = False
