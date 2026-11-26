from fastapi import APIRouter, Header, HTTPException, Request

from app.config import GITHUB_WEBHOOK_SECRET
from app.github.webhook import verify_github_signature
from app.impact_analysis.report_builder import build_impact_report
from app.incident.investigator import investigate
from app.rag.citation_validator import validate_citations
from app.rag.llm_provider import generate_answer
from app.retrieval.hybrid_retriever import retrieve
from app.ml.predict import predict_risk
from app.database.connection import database


router = APIRouter(tags=["workflows"])


@router.post("/rag/query")
def rag_query(payload: dict) -> dict:
    repository_id = str(payload.get("repository_id", "")).strip()
    question = str(payload.get("question", "")).strip()
    if not repository_id or not question:
        raise HTTPException(status_code=422, detail="repository_id and question are required")
    try:
        evidence = retrieve(repository_id, question, limit=10)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    generation = generate_answer(question, evidence)
    return {
        "answer": generation.text,
        "provider": generation.provider,
        "citations": generation.citations,
        "citation_validation": validate_citations(generation.text, evidence),
        "abstained": not evidence,
        "evidence": evidence,
    }


@router.post("/prs/analyze")
def analyze_pr(payload: dict) -> dict:
    repository_id = str(payload.get("repository_id", "")).strip()
    question = str(payload.get("pull_request_number", "")).strip()
    if not repository_id:
        raise HTTPException(status_code=422, detail="repository_id is required")
    report = build_impact_report(
        repository_id,
        payload.get("title", "") + " " + payload.get("description", "") or question,
    )
    report["risk"] = predict_risk()
    return report


@router.post("/incidents/investigate")
def investigate_incident(payload: dict) -> dict:
    repository_id = str(payload.get("repository_id", "")).strip()
    description = str(payload.get("description", "")).strip()
    if not repository_id or not description:
        raise HTTPException(status_code=422, detail="repository_id and description are required")
    return investigate(repository_id, description)


@router.post("/webhooks/github")
async def github_webhook(request: Request, x_hub_signature_256: str | None = Header(default=None)) -> dict:
    body = await request.body()
    if not GITHUB_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="GitHub webhook secret is not configured")
    if not verify_github_signature(GITHUB_WEBHOOK_SECRET, body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    event = await request.json()
    action = event.get("action")
    return {"status": "accepted", "event": "github_webhook", "action": action}
