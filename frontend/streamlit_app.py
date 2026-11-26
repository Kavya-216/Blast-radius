import os
import urllib.request
import json
import urllib.error

import streamlit as st


API_URL = os.getenv("IMPACTLENS_API_URL", "http://127.0.0.1:8000").rstrip("/")


def post(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{API_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{exc.code} {exc.reason}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Cannot reach ImpactLens API at {API_URL}. "
            "Start it with: uvicorn app.main:app --host 0.0.0.0 --port 8000"
        ) from exc


def get(path: str) -> dict:
    try:
        with urllib.request.urlopen(f"{API_URL}{path}", timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(
            f"Cannot reach ImpactLens API at {API_URL}. "
            "Start it with: uvicorn app.main:app --host 0.0.0.0 --port 8000"
        ) from exc


def show_api_error(exc: Exception) -> None:
    st.error(str(exc))
    st.caption(f"Configured API URL: {API_URL}")


st.set_page_config(page_title="ImpactLens", layout="wide")
st.title("ImpactLens")
st.caption("Evidence-grounded software change impact analysis")

repository_id = st.text_input("Repository ID", "demo")
workflow = st.sidebar.radio("Workflow", ["Engineering Q&A", "PR impact", "Incident investigation"])
st.sidebar.write(f"API: `{API_URL}`")

try:
    health = get("/health")
    st.sidebar.success(f"API connected ({health['status']})")
except RuntimeError as exc:
    show_api_error(exc)

if st.sidebar.button("Index demo repository"):
    try:
        register_req = urllib.request.Request(
            f"{API_URL}/repositories",
            data=json.dumps({
                "repository_id": "demo",
                "local_path": "data",
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(register_req, timeout=30):
            pass
        index_req = urllib.request.Request(
            f"{API_URL}/repositories/demo/index",
            data=b"",
            method="POST",
        )
        with urllib.request.urlopen(index_req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
        st.sidebar.success(
            f"Indexed demo: {result['files_seen']} files, "
            f"{result['chunks_written']} new chunks"
        )
    except Exception as exc:
        show_api_error(exc)

if workflow == "Engineering Q&A":
    question = st.text_area("Ask about code, tests, incidents, or architecture")
    if st.button("Ask") and question.strip():
        try:
            result = post("/rag/query", {"repository_id": repository_id, "question": question})
            st.markdown(result["answer"])
            if result["abstained"]:
                st.warning("Insufficient evidence was retrieved.")
            st.subheader("Evidence")
            for item in result["evidence"]:
                st.markdown(f"**{item['source_type']}: {item['file_path']}**")
                st.code(item["content"])
        except Exception as exc:
            show_api_error(exc)

elif workflow == "PR impact":
    pr_number = st.text_input("Pull request number", "1")
    title = st.text_input("PR title")
    description = st.text_area("PR description")
    if st.button("Analyze PR"):
        try:
            result = post("/prs/analyze", {
                "repository_id": repository_id,
                "pull_request_number": pr_number,
                "title": title,
                "description": description,
            })
            st.markdown(result["summary"])
            st.subheader("Evidence")
            for item in result["evidence"]:
                st.markdown(f"**{item['file_path']}**")
                st.code(item["content"])
        except Exception as exc:
            show_api_error(exc)

else:
    description = st.text_area("Incident description or stack trace")
    if st.button("Investigate") and description.strip():
        try:
            result = post("/incidents/investigate", {
                "repository_id": repository_id,
                "description": description,
            })
            st.write(result)
        except Exception as exc:
            show_api_error(exc)
