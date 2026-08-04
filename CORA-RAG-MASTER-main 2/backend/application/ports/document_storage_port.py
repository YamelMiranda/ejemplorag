"""Puerto de almacenamiento físico de los archivos subidos."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional


class DocumentStoragePort(ABC):
    @abstractmethod
    def save(self, filename: str, content: bytes) -> Path:
        raise NotImplementedError

    @abstractmethod
    def list_files(self) -> List[Path]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, filename: str) -> Optional[str]:
        """Elimina el archivo y devuelve su nombre canónico (sanitizado), o
        `None` si no existía. El caller debe usar el nombre devuelto —no el
        `filename` recibido— para limpiar otros almacenes relacionados."""
        raise NotImplementedError
