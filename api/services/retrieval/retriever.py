"""
Retrieval over two separate stores:
  1. the incident's own loaded documents (IR plan, playbooks) — Chunk table
  2. the reference corpus (NIST 800-61r3, and any future standards dropped
     into /reference-corpus) — ReferenceChunk table, rebuilt at startup by
     services/ingestion/reference_loader.py

Keeping these separate lets guidance answers cite "your IR plan says X" vs
"NIST 800-61r3 recommends Y" distinctly — results are tagged with
kind="org_doc" or kind="reference" accordingly, and merged/ranked together
here by the same scoring so the top matches can come from either store.

Implementation: TF-IDF over the combined chunk set (per the architecture
doc's "start keyword-based, move to vector if quality demands it"). Plain
term-frequency was tried first and discarded: in a corpus that's
literally an incident response standard, a word like "incident" appears
in nearly every chunk and provides no discriminating signal, but a raw
count still let it dominate ranking — NIST passages buried the org's own
IR plan sections in every test query. IDF down-weights terms that are
common across the corpus (like "incident") relative to rarer, more
specific ones (like "notify" or "legal"), which is what actually
distinguishes one chunk from another. Still no extra infra — computed
fresh per query directly against the SQLite tables ingestion populates.

Known simplification: documents aren't yet associated with a specific
incident (that requires the incident-document link the architecture doc
still lists as TODO), so `incident_id` is accepted for the API shape but
not yet used to filter — retrieval currently searches all loaded org
documents.
"""
import math
import re
from collections import Counter
from typing import Any

from sqlalchemy.orm import Session, joinedload

from db import SessionLocal
from models.documents import Chunk
from models.reference import ReferenceChunk

TOP_K = 5

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "have", "has", "had", "of", "in", "on", "at",
    "to", "for", "and", "or", "but", "if", "so", "as", "by", "with",
    "what", "when", "where", "who", "how", "why", "should", "we", "our",
    "it", "this", "that", "there", "here", "i", "you", "your", "about",
}

_WORD_RE = re.compile(r"[a-z0-9]+")

# Longest-suffix-first light stemmer — good enough to match e.g.
# "contain"/"containment"/"contained" or "eradicate"/"eradication"
# without pulling in a real NLP dependency. Not linguistically rigorous,
# just enough to stop obvious keyword-search misses.
_SUFFIXES = [
    "izations", "ization", "ations", "ation",
    "ities", "ments", "ment", "ing", "ers", "ied", "ies", "ate",
    "ery", "ed", "es", "ly", "er", "s",
]


def _stem(word: str) -> str:
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def _tokenize(text: str) -> list[str]:
    return [
        _stem(w)
        for w in _WORD_RE.findall(text.lower())
        if w not in _STOPWORDS and len(w) > 1
    ]


def get_relevant_context(incident_id: str, query: str, top_k: int = TOP_K) -> list[dict[str, Any]]:
    query_terms = set(_tokenize(query))
    if not query_terms:
        return []

    db: Session = SessionLocal()
    try:
        org_chunks = db.query(Chunk).options(joinedload(Chunk.document)).all()
        ref_chunks = db.query(ReferenceChunk).all()

        # Tokenize every chunk once, up front, so IDF can be computed over
        # the whole combined corpus before any per-chunk scoring happens.
        items = []  # (kind, source_label, raw_text, tokens)
        for chunk in org_chunks:
            searchable = f"{chunk.heading}\n{chunk.text}" if chunk.heading else chunk.text
            source = chunk.document.filename
            if chunk.heading:
                source = f"{source} — {chunk.heading}"
            items.append(("org_doc", source, chunk.text, _tokenize(searchable)))
        for chunk in ref_chunks:
            searchable = f"{chunk.heading}\n{chunk.text}" if chunk.heading else chunk.text
            source = f"NIST SP 800-61r3 — {chunk.heading}" if chunk.heading else "NIST SP 800-61r3"
            items.append(("reference", source, chunk.text, _tokenize(searchable)))

        if not items:
            return []

        n_docs = len(items)
        doc_freq = Counter()
        for _, _, _, tokens in items:
            doc_freq.update(set(tokens))

        def idf(term: str) -> float:
            return math.log((n_docs + 1) / (doc_freq.get(term, 0) + 1)) + 1

        scored = []
        for kind, source, text, tokens in items:
            if not tokens:
                continue
            tf = Counter(tokens)
            raw = sum(tf[term] * idf(term) for term in query_terms if term in tf)
            if raw <= 0:
                continue
            score = raw / (len(tokens) ** 0.5)  # length-normalize so long chunks don't win purely by size
            scored.append((score, {"text": text, "source": source, "kind": kind, "score": round(score, 4)}))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        results = scored[:top_k]

        # Guarantee representation from the org's own plan when it has any
        # relevant match — pure TF-IDF can legitimately rank several dense
        # NIST sections above a shorter, equally relevant plan section, but
        # a tool whose whole point is "what does your plan say" shouldn't
        # let the standard fully crowd it out.
        if not any(item["kind"] == "org_doc" for _, item in results):
            org_scored = [pair for pair in scored if pair[1]["kind"] == "org_doc"]
            if org_scored:
                results = results[:-1] + [org_scored[0]]
                results.sort(key=lambda pair: pair[0], reverse=True)

        return [item for _, item in results]
    finally:
        db.close()
