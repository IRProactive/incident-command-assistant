"""
Two tables:
  - documents: one row per uploaded file (IR plan, playbook, etc)
  - chunks:    the parsed/chunked text of each document, used by retrieval

Kept intentionally separate from any future reference-corpus indexing
(NIST 800-61r3 etc.) — org docs and standards are different trust levels
and update cadences, so they get their own tables/stores even though the
schema shape is similar.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship

from db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=_uuid)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending | ingested | failed
    error = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True, default=_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    ordinal = Column(Integer, nullable=False)
    heading = Column(String, nullable=True)  # nearest section heading, if detected
    text = Column(Text, nullable=False)

    document = relationship("Document", back_populates="chunks")
