"""Adapter de embeddings basado en SentenceTransformer (HuggingFace).

Misma lógica prototipada en notebook/pdfloader.ipynb, ahora detrás del
puerto `EmbeddingPort` para que la capa de aplicación no dependa de
sentence-transformers directamente.
"""
from __future__ import annotations

import warnings
from typing import List

import numpy as np

warnings.filterwarnings("ignore")

from sentence_transformers import SentenceTransformer

from backend.application.ports.embedding_port import EmbeddingPort
from backend.core.logging import get_logger

logger = get_logger(__name__)


class SentenceTransformerEmbedder(EmbeddingPort):
    def __init__(self, model_name: str):
        self._model_name = model_name
        logger.info("Cargando modelo de embeddings: %s", model_name)
        self._model = SentenceTransformer(model_name)
        logger.info(
            "Modelo de embeddings cargado. Dimensiones: %d",
            self._model.get_sentence_embedding_dimension(),
        )

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.array([])
        # normalize_embeddings=True: los vectores quedan unitarios de forma
        # explícita (no implícita/casual del modelo), consistente con el
        # espacio "cosine" configurado en ChromaVectorStore.
        return self._model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
