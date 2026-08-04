"""Caso de uso: gestión del historial de chats de CORA (listar, leer, borrar)."""
from __future__ import annotations

from typing import List

from backend.application.ports.chat_repository_port import ChatRepositoryPort
from backend.core.exceptions import AuthorizationError, NotFoundError
from backend.core.security.authorization import AccessPolicy, Action
from backend.core.security.identity import Principal
from backend.domain.chat import Chat


class ManageChatsUseCase:
    def __init__(self, chat_repository: ChatRepositoryPort, access_policy: AccessPolicy):
        self._chat_repository = chat_repository
        self._access_policy = access_policy

    def list_chats(self, principal: Principal) -> List[dict]:
        self._require(principal)
        return self._chat_repository.list_chats()

    def get_chat(self, principal: Principal, chat_id: str) -> Chat:
        self._require(principal)
        chat = self._chat_repository.get_chat(chat_id)
        if not chat:
            raise NotFoundError(f"Chat '{chat_id}' no encontrado")
        return chat

    def delete_chat(self, principal: Principal, chat_id: str) -> None:
        self._require(principal)
        if not self._chat_repository.chat_exists(chat_id):
            raise NotFoundError(f"Chat '{chat_id}' no encontrado")
        self._chat_repository.delete_chat(chat_id)

    def count_chats(self) -> int:
        return self._chat_repository.count_chats()

    def count_user_messages(self) -> int:
        return self._chat_repository.count_user_messages()

    def _require(self, principal: Principal) -> None:
        if not self._access_policy.can(principal, Action.MANAGE_CHATS, "*"):
            raise AuthorizationError(f"'{principal.id}' no está autorizado a gestionar chats")
