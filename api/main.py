"""
Incident Command Assistant — API entrypoint.

Runs on port 5001 by default (set to avoid colliding with other local
services). Change via the UVICORN_PORT env var or the docker-compose
port mapping — don't hardcode a different value here.
"""
import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import documents, incidents, guidance, settings as settings_route
from db import Base, engine
from models import documents as document_models  # noqa: F401 — registers tables with Base
from models import reference as reference_models  # noqa: F401 — registers tables with Base
from services.ingestion.reference_loader import load_reference_corpus

APP_PORT = int(os.getenv("UVICORN_PORT", "5001"))

Base.metadata.create_all(bind=engine)
_corpus_summary = load_reference_corpus()

app = FastAPI(
    title="Incident Command Assistant",
    description="Reference-aware guidance for incident leads, grounded in the loaded IR plan and standards such as NIST SP 800-61r3.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before any non-local deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(incidents.router, prefix="/incidents", tags=["incidents"])
app.include_router(guidance.router, prefix="/guidance", tags=["guidance"])
app.include_router(settings_route.router, prefix="/settings", tags=["settings"])


@app.get("/health")
def health():
    return {"status": "ok", "reference_corpus": _corpus_summary}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=APP_PORT, reload=True)
