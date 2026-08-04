"""Caso de uso compuesto: una pregunta de chat completa.

Orquesta `ChatRepositoryPort` (persistencia del historial) con
`AnswerQueryUseCase` (retrieval + generación), igual que hacía
`POST /api/chat/query` en el backend original. Se mantiene separado de
`AnswerQueryUseCase` para que el RAG puro sea reutilizable sin depender del
historial de chats (p. ej. para una futura API sin estado).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from backend.application.ports.chat_repository_port import ChatRepositoryPort
from backend.application.use_cases.answer_query import AnswerQueryUseCase
from backend.core.exceptions import ValidationError
from backend.core.security.identity import Principal
from backend.domain.chat import DocumentReference


@dataclass(frozen=True)
class ChatQueryResult:
    chat_id: str
    answer: str
    sources: List[DocumentReference]


class ChatQueryUseCase:
    def __init__(self, chat_repository: ChatRepositoryPort, answer_query: AnswerQueryUseCase):
        self._chat_repository = chat_repository
        self._answer_query = answer_query

    def execute(
        self,
        principal: Principal,
        question: str,
        chat_id: Optional[str],
        top_k: int,
        score_threshold: float,
    ) -> ChatQueryResult:
        question = question.strip()
        if not question:
            raise ValidationError("La pregunta no puede estar vacía")

        if not chat_id or not self._chat_repository.chat_exists(chat_id):
            chat_id = self._chat_repository.create_chat(title=question)

        self._chat_repository.add_message(chat_id, role="user", content=question)

        result = self._answer_query.execute(
            principal, question, top_k=top_k, score_threshold=score_threshold
        )

        self._chat_repository.add_message(
            chat_id, role="assistant", content=result.answer, sources=result.references
        )

        return ChatQueryResult(chat_id=chat_id, answer=result.answer, sources=result.references)
