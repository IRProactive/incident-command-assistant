"""
Extracts text from uploaded IR plans and other org documents, then chunks
it for retrieval.

Supported today: PDF (.pdf) and Word (.docx). Anything else is stored with
status "failed" and a clear error rather than silently mis-parsed.

Chunking is heading-aware where possible: an IR plan is structured
(sections like "Containment", "Roles and Responsibilities"), and keeping
that structure means retrieval can later cite "IR Plan — Containment"
instead of an anonymous blob of text.
"""
import io
import os

from pypdf import PdfReader
from docx import Document as DocxDocument
from sqlalchemy.orm import Session

from db import SessionLocal
from models.documents import Document, Chunk

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/data/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_CHUNK_CHARS = 1800  # keeps chunks small enough for good retrieval granularity
MIN_CHUNK_CHARS = 200   # avoid a flood of tiny fragment chunks


def _extract_pdf_text(raw: bytes) -> list[tuple[str | None, str]]:
    """Returns a list of (heading, text) blocks. PDFs have no reliable
    heading markup, so each page becomes one block; headings are left
    None and the chunker below falls back to paragraph splitting."""
    reader = PdfReader(io.BytesIO(raw))
    blocks = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            blocks.append((None, text))
    return blocks


def _extract_docx_text(raw: bytes) -> list[tuple[str | None, str]]:
    """Returns (heading, text) blocks using Word's built-in Heading styles
    as section boundaries — this is where a real IR plan's structure
    (numbered sections, RACI, severity matrix) actually shows up."""
    doc = DocxDocument(io.BytesIO(raw))
    blocks: list[tuple[str | None, str]] = []
    current_heading: str | None = None
    current_text: list[str] = []

    def flush():
        if current_text:
            blocks.append((current_heading, "\n".join(current_text).strip()))

    for para in doc.paragraphs:
        style = (para.style.name or "").lower()
        if style.startswith("heading"):
            flush()
            current_heading = para.text.strip()
            current_text = []
        elif para.text.strip():
            current_text.append(para.text)
    flush()

    # tables often carry RACI/severity-matrix content — pull them in too
    for table in doc.tables:
        rows = [" | ".join(cell.text.strip() for cell in row.cells) for row in table.rows]
        table_text = "\n".join(r for r in rows if r.strip())
        if table_text:
            blocks.append(("Table", table_text))

    return [b for b in blocks if b[1].strip()]


def _chunk_blocks(blocks: list[tuple[str | None, str]]) -> list[tuple[str | None, str]]:
    """Splits each (heading, text) block into chunks under MAX_CHUNK_CHARS,
    splitting on paragraph boundaries first and merging small fragments so
    retrieval doesn't end up with a wall of near-empty chunks."""
    chunks: list[tuple[str | None, str]] = []
    for heading, text in blocks:
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        current = ""
        for para in paragraphs:
            candidate = f"{current}\n{para}".strip() if current else para
            if len(candidate) > MAX_CHUNK_CHARS and len(current) >= MIN_CHUNK_CHARS:
                chunks.append((heading, current))
                current = para
            else:
                current = candidate
        if current:
            chunks.append((heading, current))
    return chunks


def _extract(filename: str, content_type: str | None, raw: bytes) -> list[tuple[str | None, str]]:
    lower = filename.lower()
    if lower.endswith(".pdf") or content_type == "application/pdf":
        return _extract_pdf_text(raw)
    if lower.endswith(".docx") or content_type == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        return _extract_docx_text(raw)
    raise ValueError(f"Unsupported file type for '{filename}' — only .pdf and .docx are supported today")


async def ingest(file) -> dict:
    """Reads the uploaded file, extracts + chunks text, persists a Document
    row and its Chunk rows. Returns a summary dict for the API response."""
    raw = await file.read()

    db: Session = SessionLocal()
    doc = Document(filename=file.filename, content_type=file.content_type, status="pending")
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        # keep the original on disk too — useful for re-processing later
        # with a better chunker without asking the user to re-upload
        dest = os.path.join(UPLOAD_DIR, f"{doc.id}_{file.filename}")
        with open(dest, "wb") as f:
            f.write(raw)

        blocks = _extract(file.filename, file.content_type, raw)
        if not blocks:
            raise ValueError("No extractable text found — file may be scanned/image-based or empty")

        chunked = _chunk_blocks(blocks)

        for i, (heading, text) in enumerate(chunked):
            db.add(Chunk(document_id=doc.id, ordinal=i, heading=heading, text=text))

        doc.status = "ingested"
        db.commit()
        chunk_count = len(chunked)
        # capture values before closing the session — accessing ORM attributes
        # on a detached instance raises DetachedInstanceError
        result = {"document_id": doc.id, "status": doc.status, "chunk_count": chunk_count}
    except Exception as e:
        doc.status = "failed"
        doc.error = str(e)
        db.commit()
        db.close()
        raise

    db.close()
    return result


def list_documents() -> list[dict]:
    db: Session = SessionLocal()
    try:
        docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
        return [
            {
                "id": d.id,
                "filename": d.filename,
                "status": d.status,
                "error": d.error,
                "uploaded_at": d.uploaded_at.isoformat(),
                "chunk_count": len(d.chunks),
            }
            for d in docs
        ]
    finally:
        db.close()
