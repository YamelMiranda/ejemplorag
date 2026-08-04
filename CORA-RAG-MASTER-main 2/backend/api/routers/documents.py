"""Endpoints de gestión de documentos (subir, listar, editar, eliminar)."""
from __future__ import annotations

from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel

from backend.api.dependencies import (
    get_current_principal,
    get_ingest_document_use_case,
    get_manage_documents_use_case,
)
from backend.application.use_cases.ingest_document import IngestDocumentUseCase
from backend.application.use_cases.manage_documents import ManageDocumentsUseCase
from backend.core.security.identity import Principal
from backend.domain.user import Role

router = APIRouter(prefix="/api", tags=["documents"])


class UpdateDocumentRequest(BaseModel):
    department: str
    visible_department: Optional[str] = None
    minimum_role: Role


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    department: str = Form(..., description="Área/departamento dueño del documento"),
    visible_department: Optional[str] = Form(
        None, description="Departamento que puede verlo; vacío = toda la empresa"
    ),
    minimum_role: Role = Form(Role.EMPLOYEE, description="Rol mínimo que puede verlo"),
    principal: Principal = Depends(get_current_principal),
    use_case: IngestDocumentUseCase = Depends(get_ingest_document_use_case),
) -> dict:
    content = await file.read()
    result = use_case.execute(
        principal,
        filename=file.filename,
        content=content,
        department=department,
        visible_department=visible_department or None,
        minimum_role=minimum_role,
    )
    return {
        "name": result.source_file,
        "estado": "Listo",
        "chunks": result.chunk_count,
        "document_id": result.document_id,
        "document_version": result.document_version,
    }


@router.get("/documents")
def get_documents(
    principal: Principal = Depends(get_current_principal),
    use_case: ManageDocumentsUseCase = Depends(get_manage_documents_use_case),
) -> dict:
    return {"documents": [asdict(doc) for doc in use_case.list_documents(principal)]}


@router.patch("/documents/{filename}")
def update_document(
    filename: str,
    payload: UpdateDocumentRequest,
    principal: Principal = Depends(get_current_principal),
    use_case: ManageDocumentsUseCase = Depends(get_manage_documents_use_case),
) -> dict:
    use_case.update_document(
        principal,
        filename,
        department=payload.department,
        visible_department=payload.visible_department or None,
        minimum_role=payload.minimum_role,
    )
    return {"updated": True}


@router.delete("/documents/{filename}")
def remove_document(
    filename: str,
    principal: Principal = Depends(get_current_principal),
    use_case: ManageDocumentsUseCase = Depends(get_manage_documents_use_case),
) -> dict:
    use_case.delete_document(principal, filename)
    return {"deleted": True}
