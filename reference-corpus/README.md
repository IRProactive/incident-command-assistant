# Reference Corpus

Drop source material for external standards here (e.g. NIST SP 800-61r3,
CSF 2.0, sector-specific guidance). Mounted read-only into the API
container at `/reference-corpus`.

Keeping this outside the app code means:
- Updating a standard doesn't require a code change or rebuild
- The corpus can be swapped per engagement (e.g. adding a client's
  regulatory framework) without touching ingestion logic
- It stays compatible with air-gapped deployment — just copy files in

Suggested structure:
```
reference-corpus/
├── nist-800-61r3/
├── nist-csf-2.0/
└── other-standards/
```

The retrieval service (`api/services/retrieval/retriever.py`) is where
this gets indexed — not yet implemented.
