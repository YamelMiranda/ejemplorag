"""Puerto de persistencia del historial de chats."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from backend.domain.chat import Chat, DocumentReference


class ChatRepositoryPort(ABC):
    @abstractmethod
    def init(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def create_chat(self, title: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def chat_exists(self, chat_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def add_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        sources: Optional[List[DocumentReference]] = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def list_chats(self) -> List[dict]:
        raise NotImplementedError

    @abstractmethod
    def get_chat(self, chat_id: str) -> Optional[Chat]:
        raise NotImplementedError

    @abstractmethod
    def delete_chat(self, chat_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def count_chats(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def count_user_messages(self) -> int:
        raise NotImplementedError
