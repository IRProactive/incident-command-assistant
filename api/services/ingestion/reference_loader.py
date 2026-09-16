"""
Loads the reference corpus (NIST 800-61r3 today; other standards can be
dropped in as additional .md files under their own subfolder) into the
reference_chunks table.

Runs at API startup and is idempotent: it clears and rebuilds the corpus
each time, so updating a file in /reference-corpus (which is mounted
read-only from the host) takes effect on the next container restart with
no code change — per the architecture doc's design goal.

Chunking is heading-aware, same philosophy as the org-doc ingestion in
services/ingestion/processor.py: a NIST CSF Subcategory (e.g. RS.MI-01)
should stay grouped with its own recommendations rather than getting
split mid-thought, and each chunk is tagged with the heading it came
from so retrieval can cite "NIST SP 800-61r3 — RS.MI (Incident
Mitigation)" instead of an anonymous passage.
"""
import os
import re

from sqlalchemy.orm import Session

from db import SessionLocal
from models.reference import ReferenceChunk

CORPUS_ROOT = os.getenv("REFERENCE_CORPUS_DIR", "/reference-corpus")

MAX_CHUNK_CHARS = 1800
MIN_CHUNK_CHARS = 200

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def _parse_markdown_blocks(text: str) -> list[tuple[str | None, str]]:
    """Splits markdown into (heading, text) blocks using ## and ### as
    section/subsection boundaries. Text under a subsection is tagged with
    the subsection heading; text before any subsection (but after a
    section heading) is tagged with the section heading."""
    blocks: list[tuple[str | None, str]] = []
    section: str | None = None
    subsection: str | None = None
    buffer: list[str] = []

    def flush():
        content = "\n".join(buffer).strip()
        if content:
            blocks.append((subsection or section, content))
        buffer.clear()

    for line in text.split("\n"):
        m = _HEADING_RE.match(line.strip())
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            flush()
            if level == 1:
                continue  # document title, not a chunk boundary
            elif level == 2:
                section, subsection = title, None
            else:
                subsection = title
        else:
            if line.strip():
                buffer.append(line)
            elif buffer and buffer[-1] != "":
                buffer.append("")  # preserve paragraph breaks
    flush()
    return blocks


def _chunk_blocks(blocks: list[tuple[str | None, str]]) -> list[tuple[str | None, str]]:
    """Same paragraph-aware chunking strategy as org-doc ingestion."""
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


def _find_corpus_files() -> list[tuple[str, str]]:
    """Returns (corpus_name, filepath) pairs — corpus_name is the
    top-level subfolder under /reference-corpus (e.g. 'nist-800-61r3')."""
    results = []
    if not os.path.isdir(CORPUS_ROOT):
        return results
    for entry in sorted(os.listdir(CORPUS_ROOT)):
        subdir = os.path.join(CORPUS_ROOT, entry)
        if not os.path.isdir(subdir):
            continue
        for fname in sorted(os.listdir(subdir)):
            if fname.lower().endswith((".md", ".markdown")):
                results.append((entry, os.path.join(subdir, fname)))
    return results


def load_reference_corpus() -> dict:
    """Clears and rebuilds the reference_chunks table from whatever is
    currently on disk under /reference-corpus. Safe to call on every
    startup — cheap for corpus sizes in the tens of thousands of words."""
    files = _find_corpus_files()
    db: Session = SessionLocal()
    summary = {"corpora": [], "chunk_count": 0}
    try:
        db.query(ReferenceChunk).delete()

        for corpus_name, path in files:
            with open(path, encoding="utf-8") as f:
                text = f.read()

            blocks = _parse_markdown_blocks(text)
            chunked = _chunk_blocks(blocks)

            for i, (heading, chunk_text) in enumerate(chunked):
                db.add(
                    ReferenceChunk(
                        corpus=corpus_name,
                        source_file=os.path.basename(path),
                        heading=heading,
                        ordinal=i,
                        text=chunk_text,
                    )
                )
            summary["corpora"].append({"corpus": corpus_name, "file": os.path.basename(path), "chunks": len(chunked)})
            summary["chunk_count"] += len(chunked)

        db.commit()
    finally:
        db.close()

    return summary
