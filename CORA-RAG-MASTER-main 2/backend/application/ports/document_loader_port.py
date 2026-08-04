"""Puerto de carga y chunking de documentos fuente (PDF/TXT/HTML).

Se introduce como puerto (y no como utilidad de infraestructura llamada
directamente) para que `IngestDocumentUseCase` no dependa de langchain ni de
ningún parser concreto — cumple la regla de dependencia de Clean
Architecture: la capa de aplicación solo conoce interfaces.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class RawChunk:
    content: str
    page: Optional[int]
    file_type: str


class DocumentLoaderPort(ABC):
    @abstractmethod
    def load_and_split(self, file_path: Path, chunk_size: int, chunk_overlap: int) -> List[RawChunk]:
        raise NotImplementedError
