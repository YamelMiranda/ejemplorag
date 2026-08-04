"""Autorización — Pilar II (Gestión de Identidades y Accesos) y Pilar IV
(la IA solo debe consultar lo que el usuario puede ver).

`AccessPolicy` es el puerto que los casos de uso consultan antes de subir/
eliminar un documento o gestionar chats — sigue siendo permisivo
(`NullAccessPolicy`) porque esas acciones no dependen de metadata por
documento. La visibilidad *por documento* (RBAC real: departamento + rol
jerárquico) es un chequeo distinto y más rico que no encaja en la firma
genérica de `AccessPolicy.can()`, así que vive aparte en
`can_view_document()` y se llama directo desde los casos de uso que
retornan/listan documentos (`answer_query.py`, `manage_documents.py`).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Union

from backend.core.security.identity import Principal
from backend.domain.user import Role


class Action(str, Enum):
    READ_DOCUMENT = "read_document"
    UPLOAD_DOCUMENT = "upload_document"
    UPDATE_DOCUMENT = "update_document"
    DELETE_DOCUMENT = "delete_document"
    QUERY = "query"
    MANAGE_CHATS = "manage_chats"


class AccessPolicy(ABC):
    """Puerto de autorización contextual (RBAC)."""

    @abstractmethod
    def can(self, principal: Principal, action: Action, resource: str) -> bool:
        raise NotImplementedError


class NullAccessPolicy(AccessPolicy):
    """Adapter permisivo: no hay restricciones para subir/eliminar
    documentos ni gestionar chats — cualquier usuario autenticado puede.
    La visibilidad por documento (quién ve qué) ya es real, ver
    `can_view_document()` abajo."""

    def can(self, principal: Principal, action: Action, resource: str) -> bool:
        return True


# Jerarquía de roles: un rol superior siempre incluye lo que ve uno
# inferior (EMPLOYEE ⊆ SUPERVISOR ⊆ ADMIN), tal como lo pidió el usuario:
# "si se marca que un documento puede ser visto por todos los empleados,
# eso implica que los supervisores y admins lo pueden ver también".
_ROLE_RANK = {
    Role.EMPLOYEE: 0,
    Role.SUPERVISOR: 1,
    Role.ADMIN: 2,
}


def is_admin(principal: Principal) -> bool:
    return Role.ADMIN.value in principal.roles


def _principal_role_rank(principal: Principal) -> int:
    best = -1
    for raw_role in principal.roles:
        try:
            best = max(best, _ROLE_RANK[Role(raw_role)])
        except ValueError:
            continue
    return best


def can_view_document(
    principal: Principal,
    visible_department: Optional[str],
    minimum_role: Union[Role, str],
) -> bool:
    """RBAC real de documentos (Pilar IV: la IA y "Gestión de Documentos"
    solo muestran lo que el usuario puede ver).

    ADMIN ve todo, sin excepción — incluso documentos restringidos a otro
    departamento (decisión confirmada explícitamente, no es un olvido).
    Para el resto: el rol del principal debe alcanzar `minimum_role`
    (jerárquico) Y, si el documento está restringido a un departamento
    específico, el principal debe pertenecer a ese departamento.
    """
    if is_admin(principal):
        return True

    minimum = minimum_role if isinstance(minimum_role, Role) else Role(minimum_role)
    if _principal_role_rank(principal) < _ROLE_RANK[minimum]:
        return False

    if visible_department and principal.department != visible_department:
        return False

    return True
