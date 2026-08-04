"""Puerto hacia el Repositorio de Conocimiento Empresarial.

ChromaDB es hoy el único adapter, pero el puerto no expone nada específico
de Chroma: los casos de uso solo conocen `Chunk`, `RetrievedChunk` y estas
operaciones.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np

from backend.domain.document import Chunk


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    similarity_score: float
    distance: float


class VectorStorePort(ABC):
    @abstractmethod
    def add_chunks(self, chunks: List[Chunk], embeddings: np.ndarray) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def query(self, query_embedding: np.ndarray, top_k: int) -> List[RetrievedChunk]:
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def list_source_files(self) -> Dict[str, Dict[str, Any]]:
        """Agrupa los chunks indexados por `source_file`.

        Cada entrada trae `chunks` (cantidad), `file_type` y `metadata`
        (la metadata completa de un chunk representativo del documento —
        clasificación, departamento, owner, access_level, etc. — para
        mostrarla en el detalle de "Gestión de Documentos" sin tener que
        volver a consultar ChromaDB)."""
        raise NotImplementedError

    @abstractmethod
    def delete_by_source(self, source_file: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def update_document_metadata(self, source_file: str, updates: Dict[str, Any]) -> None:
        """Actualiza campos de metadata en todos los chunks de un
        `source_file` sin regenerar embeddings — para editar
        departamento/rol visible de un documento ya indexado."""
        raise NotImplementedError
