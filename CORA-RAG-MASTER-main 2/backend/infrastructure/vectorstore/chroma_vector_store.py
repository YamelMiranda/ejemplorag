"""Adapter de ChromaDB — el Repositorio de Conocimiento Empresarial de CORA.

ChromaDB no se trata como un vector store genérico: cada chunk se persiste
con el estándar completo de metadatos de `DocumentMetadata` (16 campos),
para permitir a futuro filtrar por clasificación, departamento o nivel de
acceso sin cambiar el esquema.
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

import chromadb

from backend.application.ports.vector_store_port import RetrievedChunk, VectorStorePort
from backend.core.exceptions import RetrievalError
from backend.domain.document import Chunk


class ChromaVectorStore(VectorStorePort):
    def __init__(self, collection_name: str, persist_directory: str):
        self._client = chromadb.PersistentClient(path=persist_directory)
        # hnsw:space="cosine" es obligatorio aquí: sin esto, Chroma usa
        # distancia L2 al cuadrado por defecto, y `similarity_score = 1 -
        # distance` (más abajo) deja de ser una similitud coseno válida —
        # da porcentajes sin sentido (incluso negativos) y puede invertir
        # el ranking de los resultados. Con "cosine", Chroma calcula
        # directamente 1 - similitud_coseno, así que la fórmula sí aplica.
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={
                "description": "Repositorio de Conocimiento Empresarial de CORA",
                "hnsw:space": "cosine",
            },
        )

    def add_chunks(self, chunks: List[Chunk], embeddings: np.ndarray) -> List[str]:
        if len(chunks) != len(embeddings):
            raise ValueError("El número de chunks debe coincidir con el número de embeddings")

        ids: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        documents: List[str] = []
        embeddings_list: List[List[float]] = []

        for chunk, embedding in zip(chunks, embeddings):
            ids.append(chunk.metadata.chunk_id)
            metadatas.append(chunk.metadata.to_chroma_metadata())
            documents.append(chunk.content)
            embeddings_list.append(embedding.tolist())

        self._collection.add(
            ids=ids,
            embeddings=embeddings_list,
            metadatas=metadatas,
            documents=documents,
        )
        return ids

    def query(self, query_embedding: np.ndarray, top_k: int) -> List[RetrievedChunk]:
        if self.count() == 0:
            return []

        try:
            results = self._collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=min(top_k, self.count()),
            )
        except Exception as exc:
            raise RetrievalError(f"Falló la búsqueda en el Repositorio de Conocimiento: {exc}") from exc

        retrieved: List[RetrievedChunk] = []
        documents = results.get("documents") or [[]]
        if documents and documents[0]:
            for chunk_id, content, metadata, distance in zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                retrieved.append(
                    RetrievedChunk(
                        chunk_id=chunk_id,
                        content=content,
                        metadata=metadata,
                        similarity_score=1 - distance,
                        distance=distance,
                    )
                )
        return retrieved

    def count(self) -> int:
        return self._collection.count()

    def list_source_files(self) -> Dict[str, Dict[str, Any]]:
        summary: Dict[str, Dict[str, Any]] = {}
        if self.count() == 0:
            return summary

        result = self._collection.get(include=["metadatas"])
        for metadata in result.get("metadatas", []) or []:
            source = metadata.get("source_file", "desconocido")
            entry = summary.setdefault(
                source,
                {
                    "chunks": 0,
                    "file_type": metadata.get("file_type", "desconocido"),
                    # metadata completa de un chunk representativo (todos
                    # los chunks de un mismo source_file comparten
                    # clasificación/departamento/owner/access_level).
                    "metadata": metadata,
                },
            )
            entry["chunks"] += 1
        return summary

    def delete_by_source(self, source_file: str) -> None:
        self._collection.delete(where={"source_file": source_file})

    def update_document_metadata(self, source_file: str, updates: Dict[str, Any]) -> None:
        result = self._collection.get(where={"source_file": source_file})
        ids = result.get("ids") or []
        if not ids:
            return

        # A diferencia de `add()` (que rechaza None de plano, ver
        # `DocumentMetadata.to_chroma_metadata`), `collection.update()` sí
        # acepta None como valor y lo usa para *borrar* esa clave del
        # documento — confirmado empíricamente. Si en cambio se omite la
        # clave del dict, Chroma conserva el valor anterior (no es un
        # reemplazo completo), así que hay que enviar cada campo de
        # `updates` explícitamente, incluidos los None.
        self._collection.update(ids=ids, metadatas=[dict(updates) for _ in ids])
