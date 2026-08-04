"""Adapter de carga y chunking de documentos, basado en langchain
(PyMuPDFLoader/TextLoader + RecursiveCharacterTextSplitter) — misma lógica
prototipada en notebook/document.ipynb y notebook/pdfloader.ipynb, ahora
detrás de `DocumentLoaderPort`.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.application.ports.document_loader_port import DocumentLoaderPort, RawChunk
from backend.core.exceptions import IngestionError
from backend.domain.document import FileType


def _file_type_for(suffix: str) -> FileType:
    if suffix == ".pdf":
        return FileType.PDF
    if suffix in (".html", ".htm"):
        return FileType.HTML
    return FileType.TXT


class LangchainDocumentLoader(DocumentLoaderPort):
    def load_and_split(self, file_path: Path, chunk_size: int, chunk_overlap: int) -> List[RawChunk]:
        suffix = file_path.suffix.lower()
        try:
            if suffix == ".pdf":
                documents = PyMuPDFLoader(str(file_path)).load()
            else:
                documents = TextLoader(str(file_path), encoding="utf-8").load()
        except Exception as exc:
            raise IngestionError(f"No se pudo cargar el archivo '{file_path.name}': {exc}") from exc

        file_type = _file_type_for(suffix)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", "", ","],
        )
        split_docs = splitter.split_documents(documents)

        return [
            RawChunk(
                content=doc.page_content,
                page=doc.metadata.get("page"),
                file_type=file_type.value,
            )
            for doc in split_docs
        ]
