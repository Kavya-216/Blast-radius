import os
import urllib.request
import json

import streamlit as st


API_URL = os.getenv("IMPACTLENS_API_URL", "http://127.0.0.1:8000")


def post(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{API_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


st.set_page_config(page_title="ImpactLens", layout="wide")
st.title("ImpactLens")
st.caption("Evidence-grounded software change impact analysis")

repository_id = st.text_input("Repository ID", "demo")
workflow = st.sidebar.radio("Workflow", ["Engineering Q&A", "PR impact", "Incident investigation"])

if workflow == "Engineering Q&A":
    question = st.text_area("Ask about code, tests, incidents, or architecture")
    if st.button("Ask") and question.strip():
        result = post("/rag/query", {"repository_id": repository_id, "question": question})
        st.markdown(result["answer"])
        if result["abstained"]:
            st.warning("Insufficient evidence was retrieved.")
        st.subheader("Evidence")
        for item in result["evidence"]:
            st.markdown(f"**{item['source_type']}: {item['file_path']}**")
            st.code(item["content"])

elif workflow == "PR impact":
    pr_number = st.text_input("Pull request number", "1")
    title = st.text_input("PR title")
    description = st.text_area("PR description")
    if st.button("Analyze PR"):
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

else:
    description = st.text_area("Incident description or stack trace")
    if st.button("Investigate") and description.strip():
        result = post("/incidents/investigate", {
            "repository_id": repository_id,
            "description": description,
        })
        st.write(result)
