"""
Reference corpus chunks (NIST 800-61r3 and, eventually, other standards).
Kept in its own table, separate from org-doc Chunk, because these come
from a different source of trust and a different update cadence — the
reference corpus is reloaded from /reference-corpus on every startup,
while org docs are uploaded once and persisted.
"""
import uuid

from sqlalchemy import Column, String, Text, Integer
from db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ReferenceChunk(Base):
    __tablename__ = "reference_chunks"

    id = Column(String, primary_key=True, default=_uuid)
    corpus = Column(String, nullable=False, index=True)  # e.g. "nist-800-61r3"
    source_file = Column(String, nullable=False)
    heading = Column(String, nullable=True)
    ordinal = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
