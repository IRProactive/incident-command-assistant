# Incident Command Assistant — Architecture Notes

## Concept
Incident lead loads the org's IR plan (and other docs). The app provides
guidance grounded in that plan plus external standards (NIST SP 800-61r3
and others), aware of the incident's current lifecycle phase.

## Ports
- API: **5001** (host and container) — chosen to avoid collisions with
  other local services. Override via `UVICORN_PORT` env var if needed,
  but keep the docker-compose host mapping in sync.
- Frontend dev server: 5173 (Vite default) — change freely, it's less
  likely to collide.

## Service boundaries
- **ingestion** (`api/services/ingestion/`) — parses/chunks uploaded org
  documents (IR plan, playbooks, contact lists). Separate from reference
  corpus loading so chunking strategy can differ.
- **retrieval** (`api/services/retrieval/`) — searches two distinct
  stores: the incident's own docs, and the read-only reference corpus.
  Chunks are tagged by source/kind so answers can distinguish "your plan"
  from "the standard."
- **guidance** (`api/services/guidance/`) — takes retrieved context +
  the incident lead's question, calls the configured LLM provider
  (`LLM_PROVIDER` env var: `none`/`openai`/`anthropic`/`local`), returns
  a grounded answer.

## Incident state
Modeled as a first-class object (see `api/routes/incidents.py`), not just
chat history — phase (mapped to the NIST 800-61r3 lifecycle), severity,
roles, timeline. This lets guidance be phase-aware rather than generic.

NIST SP 800-61r3 lifecycle phases used for `phase`:
`preparation → detection_analysis → containment → eradication → recovery
→ post_incident_activity`

## Reference corpus
Lives in `reference-corpus/`, mounted read-only into the API container.
Update standards by dropping files in — no rebuild needed once the
retrieval indexer is implemented.

## Status / next steps
- [x] Implement real ingestion (PDF/DOCX extraction + heading-aware chunking,
      persisted via SQLAlchemy — `api/services/ingestion/processor.py`)
- [x] Frontend upload UI (drag/drop + browse, status list —
      `frontend/src/components/DocumentUpload.jsx`, `DocumentList.jsx`)
- [x] Retrieval indexing over ingested chunks (TF-IDF scoring —
      `api/services/retrieval/retriever.py`)
- [x] Index the reference corpus (NIST SP 800-61r3) — loaded from
      `reference-corpus/nist-800-61r3/NIST.SP.800-61r3.md` into a
      dedicated `reference_chunks` table on every API startup
- [x] Wire an LLM provider — Anthropic, via `services/guidance/advisor.py`.
      Provider/key/model are runtime-configurable (`services/config.py`,
      `/settings` endpoint) so the frontend Settings panel can supply an
      API key without a rebuild. Frontend `AskPanel` exercises the full
      `/guidance/ask` flow for manual testing.
- [ ] Persist incidents to DB (currently stubbed) and connect the phase
      tracker to real incident state instead of a hardcoded phase
- [ ] Associate documents with a specific incident — retrieval currently
      searches all loaded org docs regardless of `incident_id`
- [ ] Add more standards to the reference corpus as needed — drop another
      well-structured `.md` file (heading-per-section, like the NIST one)
      into a new subfolder under `reference-corpus/`, restart, done

## LLM guidance layer notes
- Provider: Anthropic only for now (`services/guidance/advisor.py`).
  `LLM_PROVIDER=none` (the default) keeps everything offline — retrieval
  and its sources still work, just without a synthesized answer.
- **Runtime-configurable, not build-time.** `services/config.py` holds
  provider/model/API key in memory (not the database, not disk) and can
  be read/written via `GET`/`POST /settings/`. The frontend's Settings
  panel (`SettingsPanel.jsx`) POSTs to this — enter a key, hit Save, ask
  a question immediately, no container restart needed. `GET /settings/`
  never returns the key itself, only whether one is configured.
- The in-memory choice is deliberate: an API key typed into a web form
  shouldn't end up in a SQLite file or a mounted volume. Tradeoff: the
  key is lost on restart. For deployments where re-entering it each
  restart is unacceptable, set `ANTHROPIC_API_KEY`/`LLM_PROVIDER` as env
  vars in `docker-compose.yml` instead — those seed the initial value,
  and the UI can still override for the running session.
- **Version pin caught by testing:** `anthropic==0.39.0` (the version
  first pinned) fails at client construction against modern `httpx`
  (`TypeError: unexpected keyword argument 'proxies'`). Pinned to
  `anthropic==0.120.2` instead, which doesn't hit this. Worth
  re-checking if bumping either dependency later.
- Verified end-to-end with a deliberately invalid key: settings
  save/read round-trips correctly (key never echoed back), retrieval and
  sources still return normally, and the auth failure surfaces as a
  clean, specific message ("Anthropic rejected the configured API key")
  rather than a stack trace or a hang. Have not yet verified an actual
  successful synthesis with a valid key — that needs a real key to test.

## Reference corpus notes
- Source: the official final NIST SP 800-61r3 publication
  (nvlpubs.nist.gov), a U.S. government work not subject to copyright.
  Restructured into markdown with `##` section headings and `###`
  CSF-Category headings (GV, ID, PR, DE, RS, RC) so ingestion produces
  per-Category chunks rather than one giant blob.
- `services/ingestion/reference_loader.py` rebuilds the `reference_chunks`
  table from `/reference-corpus` on every startup — editing or adding a
  corpus file just needs a container restart, no code change.
- To add another standard: create `reference-corpus/<name>/<file>.md`
  with the same heading convention and restart. The loader picks up any
  `.md`/`.markdown` file under any subfolder automatically.

## Retrieval notes
- **TF-IDF**, not raw term frequency — this was a real bug caught during
  testing, not a hypothetical. Early raw-frequency scoring let common
  domain words (e.g. "incident," present in nearly every NIST chunk)
  dominate ranking and completely buried the org's own IR plan sections
  in every test query. IDF down-weights terms that are common across the
  whole corpus in favor of ones that actually discriminate between
  chunks (e.g. "notify," "legal").
- Query and chunk text are tokenized (lowercased, punctuation stripped, a
  stopword list removed, then lightly stemmed so e.g. "contain" matches
  "containment"/"contained"). Score is length-normalized so long chunks
  don't win purely by repeating a term more times.
- At least one org-doc result is guaranteed to appear when the org's
  plan has any relevant match at all — pure TF-IDF can still legitimately
  rank several dense NIST sections above a shorter, equally relevant
  plan section, but a tool whose whole point is "what does your plan
  say" shouldn't let the standard fully crowd it out. Verified this does
  *not* fire on queries with no real org-doc relevance (confirmed with a
  CSF-2.0-only question and a nonsense query — both returned clean
  NIST-only or empty results, no forced/irrelevant org-doc entry).
- Verified end-to-end against a sample IR plan + the real NIST corpus:
  containment/eradication and notification questions each returned a mix
  of the most relevant NIST CSF Subcategories *and* the matching org-doc
  section.

## Ingestion notes
- Supported today: `.pdf` (page-level text extraction, no heading
  detection — PDFs don't carry reliable structure) and `.docx` (uses
  Word's Heading styles as section boundaries, plus table extraction for
  RACI/severity-matrix content).
- Chunks target ~1800 chars, merging small paragraph fragments to avoid a
  flood of near-empty chunks.
- Unsupported file types return a 422 with a clear message rather than
  failing silently; a document whose extraction fails is stored with
  `status: failed` and the error message, not just dropped.
- Original files are kept on disk (`UPLOAD_DIR`, mounted into the `db`
  volume) so re-ingestion with a better chunker later doesn't require
  re-upload.

## Milestone suggestion
Get ingestion + retrieval working against just the IR plan first (no LLM,
no reference corpus) — confirm the incident lead can query "what does our
plan say to do here." Then layer in the NIST corpus and guidance
generation.
