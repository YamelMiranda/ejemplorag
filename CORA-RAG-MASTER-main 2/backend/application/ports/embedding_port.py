"""Puerto para generar embeddings de texto."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

import numpy as np


class EmbeddingPort(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def embed(self, texts: List[str]) -> np.ndarray:
        raise NotImplementedError
