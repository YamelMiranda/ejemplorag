"""Caso de uso: responder una pregunta usando el pipeline RAG.

Pilar IV (IA Confiable): si no hay evidencia suficiente o autorizada, CORA
debe decir que no dispone de información verificable en vez de inventar una
respuesta. Los puntos de extensión para autorización contextual, Prompt
Guard y validación de respuesta quedan marcados explícitamente abajo: no se
implementan todavía, pero este es el lugar donde deben conectarse.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from backend.application.ports.embedding_port import EmbeddingPort
from backend.application.ports.llm_port import LLMPort
from backend.application.ports.vector_store_port import RetrievedChunk, VectorStorePort
from backend.core.exceptions import AuthorizationError
from backend.core.security.audit import AuditEvent, AuditLogger
from backend.core.security.authorization import AccessPolicy, Action, can_view_document
from backend.core.security.identity import Principal
from backend.domain.chat import DocumentReference
from backend.domain.user import Role

_NO_EVIDENCE_ANSWER = (
    "No encontré información relevante en los documentos de la empresa para "
    "responder esta pregunta. Prueba reformularla o súbele a CORA el "
    "documento que contenga esta información."
)

_PROMPT_TEMPLATE = """Eres CORA, la asistente de conocimiento interno de la empresa.
Responde la pregunta del usuario ÚNICAMENTE con base en el siguiente contexto,
extraído de los documentos internos de la empresa. Si el contexto no contiene
la respuesta, dilo claramente en vez de inventar información. Responde en
español, de forma clara y profesional.

Contexto:
{context}

Pregunta: {query}
"""


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    references: List[DocumentReference]


class AnswerQueryUseCase:
    def __init__(
        self,
        embedder: EmbeddingPort,
        vector_store: VectorStorePort,
        llm: LLMPort,
        access_policy: AccessPolicy,
        audit_logger: AuditLogger,
        relative_score_margin: float = 0.15,
    ):
        self._embedder = embedder
        self._vector_store = vector_store
        self._llm = llm
        self._access_policy = access_policy
        self._audit_logger = audit_logger
        self._relative_score_margin = relative_score_margin

    def execute(
        self, principal: Principal, query: str, top_k: int, score_threshold: float
    ) -> AnswerResult:
        if not self._access_policy.can(principal, Action.QUERY, "chat"):
            raise AuthorizationError(f"'{principal.id}' no está autorizado a consultar a CORA")

        if self._vector_store.count() == 0:
            return AnswerResult(answer=_NO_EVIDENCE_ANSWER, references=[])

        query_embedding = self._embedder.embed([query])[0]
        candidates = self._vector_store.query(query_embedding, top_k=top_k)

        # Autorización contextual real (Pilar IV): CORA solo cita chunks que
        # el principal actual puede ver — departamento + rol jerárquico
        # (ver core/security/authorization.py: can_view_document). ADMIN ve
        # todo, sin excepción.
        authorized = [
            c
            for c in candidates
            if can_view_document(
                principal,
                c.metadata.get("visible_department"),
                c.metadata.get("minimum_role", Role.EMPLOYEE.value),
            )
        ]

        results = [c for c in authorized if c.similarity_score >= score_threshold]

        # Piso relativo: con un corpus desbalanceado (un documento con
        # muchos más chunks que otro tiene más chances de colar un
        # resultado mediocre), un piso absoluto no alcanza — un documento
        # sin relación real con la pregunta puede igual superarlo. Aquí se
        # descartan los candidatos que queden muy por debajo del mejor
        # resultado de esta consulta puntual, para no mezclar la fuente
        # correcta con una claramente más débil solo porque ambas pasaron
        # el piso absoluto.
        if results:
            top_score = max(c.similarity_score for c in results)
            relative_floor = top_score - self._relative_score_margin
            results = [c for c in results if c.similarity_score >= relative_floor]

        if not results:
            self._audit_logger.record(
                AuditEvent(
                    actor=principal.id,
                    action=Action.QUERY.value,
                    resource=query,
                    success=True,
                    details={"result": "no_evidence"},
                )
            )
            return AnswerResult(answer=_NO_EVIDENCE_ANSWER, references=[])

        # TODO(seguridad, Pilar IV): Prompt Guard — sanitizar `query` y el
        # contenido recuperado antes de construir el prompt, para mitigar
        # prompt injection proveniente de documentos indexados.
        context = "\n\n".join(chunk.content for chunk in results)
        prompt = _PROMPT_TEMPLATE.format(context=context, query=query)

        answer = self._llm.generate(prompt)

        # TODO(seguridad, Pilar IV): validación de respuesta — verificar que
        # `answer` esté efectivamente sustentada por `results` antes de
        # devolverla (p. ej. detección de alucinaciones / RA-RAG).

        # El LLM recibe todos los chunks del top_k como contexto (más
        # contexto del mismo documento ayuda a la respuesta), pero al
        # usuario se le muestra una sola referencia por documento fuente
        # —la de mayor similitud— para no repetir la misma fuente varias
        # veces con porcentajes distintos.
        best_chunk_per_source: Dict[str, RetrievedChunk] = {}
        for chunk in results:
            source = chunk.metadata.get("source_file", "desconocido")
            current_best = best_chunk_per_source.get(source)
            if current_best is None or chunk.similarity_score > current_best.similarity_score:
                best_chunk_per_source[source] = chunk

        references = [
            DocumentReference(
                chunk_id=chunk.chunk_id,
                source_file=chunk.metadata.get("source_file", "desconocido"),
                file_type=chunk.metadata.get("file_type", "desconocido"),
                page=chunk.metadata.get("page"),
                similarity_score=round(chunk.similarity_score, 4),
                snippet=chunk.content[:280],
            )
            for chunk in sorted(
                best_chunk_per_source.values(), key=lambda c: c.similarity_score, reverse=True
            )
        ]

        self._audit_logger.record(
            AuditEvent(
                actor=principal.id,
                action=Action.QUERY.value,
                resource=query,
                success=True,
                details={"chunks_used": [r.chunk_id for r in references]},
            )
        )

        return AnswerResult(answer=answer, references=references)
