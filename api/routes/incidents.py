"""
Incident state is first-class here, not just chat history: phase (mapped to
the NIST 800-61r3 lifecycle), severity, assigned roles, and timeline. This is
what lets the guidance layer be context-aware instead of answering generically.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter()

# Mirrors the NIST SP 800-61r3 lifecycle phases
LIFECYCLE_PHASES = [
    "preparation",
    "detection_analysis",
    "containment",
    "eradication",
    "recovery",
    "post_incident_activity",
]


class IncidentCreate(BaseModel):
    name: str
    severity: Optional[str] = None
    phase: str = "detection_analysis"


class Incident(IncidentCreate):
    id: str
    created_at: datetime


@router.post("/")
async def create_incident(incident: IncidentCreate):
    # TODO: persist to DB; stub returns an echo for now
    return {"id": "stub-id", "created_at": datetime.utcnow().isoformat(), **incident.dict()}


@router.get("/{incident_id}")
async def get_incident(incident_id: str):
    # TODO: fetch from DB
    return {"id": incident_id, "phase": "detection_analysis"}


@router.patch("/{incident_id}/phase")
async def update_phase(incident_id: str, phase: str):
    if phase not in LIFECYCLE_PHASES:
        return {"error": f"phase must be one of {LIFECYCLE_PHASES}"}
    # TODO: persist phase transition + timestamp to timeline
    return {"id": incident_id, "phase": phase}
