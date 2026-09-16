"""
Endpoints for uploading and managing the incident lead's source documents
(IR plan, playbooks, contact lists, etc). Ingestion parses and chunks these
separately from the reference corpus (NIST 800-61r3 and friends) so the two
can be tuned independently.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException

from services.ingestion import processor

router = APIRouter()

ALLOWED_EXTENSIONS = (".pdf", ".docx")


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Accepts a document (IR plan, runbook, etc), extracts and chunks its
    text, and persists it for retrieval. Returns 422 for unsupported file
    types rather than silently failing."""
    if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type — only {', '.join(ALLOWED_EXTENSIONS)} are supported today",
        )
    try:
        result = await processor.ingest(file)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"filename": file.filename, **result}


@router.get("/")
async def list_documents():
    """Lists documents currently loaded, with ingestion status and chunk counts."""
    return processor.list_documents()
