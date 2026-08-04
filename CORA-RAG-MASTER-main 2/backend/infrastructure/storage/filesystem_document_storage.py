"""Adapter de almacenamiento físico sobre el filesystem local
(data/pdf, data/text_files).

A diferencia del backend original, re-subir un archivo con el mismo nombre
sobrescribe su contenido en vez de renombrarlo con un timestamp: el
versionado ahora lo gobierna el registro de documentos
(`backend.application.ports.document_registry_port`), que sí conserva
`document_id` estable y `document_version` incremental por archivo fuente.

`filename` llega directamente de la request HTTP (nombre del archivo
subido o parámetro de ruta al eliminar): nunca se usa tal cual para
construir una ruta en disco. Se normaliza con `Path(filename).name` para
descartar cualquier componente de directorio (`../`, rutas absolutas) antes
de tocar el filesystem — mitiga path traversal (OWASP Top 10 A01).
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Set

from backend.application.ports.document_storage_port import DocumentStoragePort
from backend.core.exceptions import ValidationError


def _safe_filename(filename: str) -> str:
    safe_name = Path(filename).name
    if not safe_name or safe_name in (".", ".."):
        raise ValidationError(f"Nombre de archivo inválido: '{filename}'")
    return safe_name


class FilesystemDocumentStorage(DocumentStoragePort):
    def __init__(self, pdf_dir: Path, text_dir: Path, allowed_extensions: List[str]):
        self._pdf_dir = pdf_dir
        self._text_dir = text_dir
        self._allowed_extensions: Set[str] = set(allowed_extensions)

    def _target_dir_for(self, filename: str) -> Path:
        suffix = Path(filename).suffix.lower()
        return self._pdf_dir if suffix == ".pdf" else self._text_dir

    def save(self, filename: str, content: bytes) -> Path:
        safe_name = _safe_filename(filename)
        suffix = Path(safe_name).suffix.lower()
        if suffix not in self._allowed_extensions:
            raise ValidationError(
                f"Extensión '{suffix}' no soportada. Formatos permitidos: "
                f"{', '.join(sorted(self._allowed_extensions))}"
            )

        target_path = self._target_dir_for(safe_name) / safe_name
        target_path.write_bytes(content)
        return target_path

    def list_files(self) -> List[Path]:
        files: List[Path] = []
        for directory in (self._pdf_dir, self._text_dir):
            if directory.exists():
                files.extend(p for p in directory.iterdir() if p.is_file())
        return files

    def delete(self, filename: str) -> Optional[str]:
        safe_name = _safe_filename(filename)
        deleted = False
        for directory in (self._pdf_dir, self._text_dir):
            candidate = directory / safe_name
            if candidate.exists():
                candidate.unlink()
                deleted = True
        return safe_name if deleted else None
