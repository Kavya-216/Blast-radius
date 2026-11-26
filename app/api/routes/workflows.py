from fastapi import APIRouter, Header, HTTPException, Request

from app.config import GITHUB_WEBHOOK_SECRET
from app.database.connection import database
from app.github.pull_requests import fetch_pull_request_diff
from app.github.webhook import verify_github_signature
from app.impact_analysis.report_builder import build_impact_report
from app.incident.investigator import investigate
from app.rag.citation_validator import validate_citations
from app.rag.llm_provider import generate_answer
from app.retrieval.hybrid_retriever import retrieve
from app.ml.predict import predict_risk


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
    if not repository_id:
        raise HTTPException(status_code=422, detail="repository_id is required")

    raw_pull_request_number = payload.get("pull_request_number", "")
    if isinstance(raw_pull_request_number, bool) or not isinstance(
        raw_pull_request_number, (str, int)
    ):
        raise HTTPException(
            status_code=422, detail="pull_request_number must be a positive integer"
        )
    number_text = str(raw_pull_request_number).strip()
    if (
        not number_text
        or not number_text.isascii()
        or not number_text.isdecimal()
        or len(number_text) > 20
    ):
        raise HTTPException(
            status_code=422, detail="pull_request_number must be a positive integer"
        )
    pull_request_number = int(number_text)
    if pull_request_number < 1:
        raise HTTPException(
            status_code=422, detail="pull_request_number must be a positive integer"
        )

    title = payload.get("title", "")
    description = payload.get("description", "")
    if not isinstance(title, str) or not isinstance(description, str):
        raise HTTPException(status_code=422, detail="title and description must be strings")

    with database() as connection:
        repository = connection.execute(
            "SELECT local_path, remote_url FROM repositories WHERE repository_id=?",
            (repository_id,),
        ).fetchone()
    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    pull_request = None
    if repository["remote_url"] and not repository["local_path"]:
        try:
            pull_request = fetch_pull_request_diff(
                repository["remote_url"], pull_request_number
            )
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    query_parts = [title.strip(), description.strip()]
    if pull_request:
        query_parts.extend(pull_request["changed_files"])
        query_parts.append(pull_request["change_context"])
    question = "\n".join(part for part in query_parts if part)
    if not question:
        question = f"pull request {pull_request_number}"

    try:
        report = build_impact_report(repository_id, question)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if pull_request:
        changed_files = pull_request["changed_files"]
        report["pull_request"] = {
            "number": pull_request_number,
            "changed_files": changed_files,
            "additions": pull_request["additions"],
            "deletions": pull_request["deletions"],
            "diff_truncated": pull_request["diff_truncated"],
            "change_context_truncated": pull_request["change_context_truncated"],
        }
        report["summary"] = (
            f"Live diff for PR #{pull_request_number} changes {len(changed_files)} "
            f"files (+{pull_request['additions']}/-{pull_request['deletions']}). "
            f"{report['summary']}"
        )
        if pull_request["diff_excerpt"]:
            report["evidence"].insert(0, {
                "chunk_id": f"github-pr:{repository_id}:{pull_request_number}",
                "file_path": f"GitHub PR #{pull_request_number} diff",
                "symbol_name": "Unified diff",
                "source_type": "diff",
                "content": pull_request["diff_excerpt"],
                "rrf_score": 1.0,
            })
        changed_test_paths = [
            path for path in changed_files
            if any(
                part in {"test", "tests", "spec", "specs"}
                for part in path.lower().split("/")
            )
            or path.lower().rsplit("/", 1)[-1].startswith(("test_", "test-"))
            or path.lower().endswith(("_test.py", "_spec.py"))
        ]
        report["tests"] = list(dict.fromkeys(report["tests"] + changed_test_paths))
        if pull_request["diff_truncated"] or pull_request["change_context_truncated"]:
            report["uncertainties"].append(
                "Diff evidence is bounded: the display excerpt is capped at 20,000 characters "
                "and changed-line retrieval context at 10,000 characters."
            )
        if not pull_request["diff"]:
            report["uncertainties"].append(
                "GitHub returned no diff content for this pull request."
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
