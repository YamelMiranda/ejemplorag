"""Puerto hacia el directorio de usuarios (hoy simulado en SQLite; mañana
podría ser un adapter LDAP/Active Directory real — ver
`backend.domain.user`).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from backend.domain.user import Role, User


class UserDirectoryPort(ABC):
    @abstractmethod
    def init(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def authenticate(self, email: str, password: str) -> Optional[User]:
        """Verifica credenciales. Devuelve el usuario si son válidas y la
        cuenta está activa; `None` en cualquier otro caso (usuario
        inexistente, contraseña incorrecta o cuenta inactiva) — nunca se
        distingue el motivo hacia el caller, para no filtrar qué correos
        existen."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]:
        raise NotImplementedError

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        raise NotImplementedError

    @abstractmethod
    def list_users(self) -> List[User]:
        raise NotImplementedError

    @abstractmethod
    def create_user(
        self, email: str, full_name: str, department: str, role: Role, password: str
    ) -> User:
        raise NotImplementedError

    @abstractmethod
    def update_user(
        self,
        user_id: str,
        *,
        full_name: Optional[str] = None,
        department: Optional[str] = None,
        role: Optional[Role] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[User]:
        raise NotImplementedError

    @abstractmethod
    def delete_user(self, user_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def touch_last_login(self, user_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_password(self, user_id: str, new_password: str, *, must_change_password: bool) -> None:
        """Hashea `new_password` internamente y la guarda, actualizando
        también la bandera de reinicio forzado (Pilar II)."""
        raise NotImplementedError
