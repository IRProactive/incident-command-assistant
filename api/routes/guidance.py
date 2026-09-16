"""
Guidance generation: given the incident's current phase and a question from
the incident lead, retrieves relevant passages from both the loaded IR plan
and the reference corpus (800-61r3, etc.), then asks the LLM layer to answer
grounded in those passages.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from services.retrieval import retriever
from services.guidance import advisor

router = APIRouter()


class GuidanceRequest(BaseModel):
    incident_id: str
    question: str


@router.post("/ask")
async def ask(request: GuidanceRequest):
    context_chunks = retriever.get_relevant_context(
        incident_id=request.incident_id,
        query=request.question,
    )
    answer = await advisor.generate_guidance(
        question=request.question,
        context_chunks=context_chunks,
    )
    return {
        "answer": answer,
        "sources": [{"source": c["source"], "kind": c["kind"]} for c in context_chunks],
    }
