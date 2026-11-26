import os
import urllib.request
import json
import urllib.error

import streamlit as st


API_URL = os.getenv("IMPACTLENS_API_URL", "http://127.0.0.1:8000").rstrip("/")


def post(path: str, payload: dict, timeout: int = 30) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{API_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
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


def connect_github_repository() -> None:
    github_url = st.session_state.get("github_repository_url", "").strip()
    if not github_url:
        st.session_state["github_connection_error"] = "Enter a GitHub repository URL."
        return
    try:
        connected = post(
            "/repositories/connect-github",
            {"remote_url": github_url},
        )
        st.session_state["repository_id"] = connected["repository_id"]
        st.session_state["github_connection_message"] = (
            "Connected without cloning. Relevant files will be fetched when you ask."
        )
    except Exception as exc:
        st.session_state["github_connection_error"] = str(exc)


def render_evidence(items: list[dict]) -> None:
    if not items:
        st.info("No evidence was retrieved for this request.")
        return
    for item in items:
        with st.expander(
            f"{item['file_path']}  ·  {item['source_type']}",
            expanded=False,
        ):
            if item.get("symbol_name"):
                st.caption(f"Symbol: {item['symbol_name']}")
            st.code(item["content"], language="python" if item["source_type"] == "python" else "markdown")


st.set_page_config(page_title="ImpactLens", layout="wide")
st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] { background: #f7f9fc; color: #172033; }
    .main .block-container { max-width: 1120px; padding-top: 1.6rem; padding-bottom: 3.5rem; }
    section[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #dce3ed; }
    .main p, .main label, .main h1, .main h2, .main h3, .main h4 { color: #172033; }
    .impact-hero {
        padding: 1.5rem 1.8rem; border-radius: 14px; margin-bottom: 1.2rem;
        color: #ffffff; background: #173b70; border-left: 6px solid #3273c5;
    }
    .impact-hero .eyebrow { color: #e3edff; font-size: .72rem; font-weight: 750; letter-spacing: .11em; }
    .impact-hero h1 { color: #ffffff !important; margin: .28rem 0 .35rem; font-size: 2rem; }
    .impact-hero p { color: #ffffff !important; margin: 0; font-size: 1rem; }
    div.stButton > button[kind="primary"] {
        border: 1px solid #174b91; border-radius: 8px; color: #ffffff !important;
        background: #205da8; font-weight: 650; padding: .5rem 1rem;
    }
    div.stButton > button[kind="primary"]:hover { background: #174b91; border-color: #123d77; }
    div[data-testid="stExpander"] { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; }
    div[data-testid="stAlert"] { border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "repository_id" not in st.session_state:
    st.session_state["repository_id"] = "demo"
workflow = st.radio(
    "Choose a workflow",
    ["Ask the repository", "Analyze a PR", "Investigate an incident"],
    horizontal=True,
    label_visibility="collapsed",
)

st.sidebar.markdown("## ImpactLens")
st.sidebar.caption("Repository change intelligence")
try:
    health = get("/health")
    st.sidebar.success("API connected")
except RuntimeError as exc:
    show_api_error(exc)
st.sidebar.caption(f"API endpoint · {API_URL}")
repository_id = st.sidebar.text_input("Active repository ID", key="repository_id")
st.sidebar.caption("Connect a public GitHub repository to query its files without cloning.")

with st.sidebar.form("github_import"):
    st.text_input(
        "Public GitHub repository URL",
        placeholder="https://github.com/HKUDS/RAG-Anything.git",
        key="github_repository_url",
    )
    st.form_submit_button(
        "Connect without cloning",
        on_click=connect_github_repository,
    )

if message := st.session_state.pop("github_connection_message", None):
    st.sidebar.success(message)
if error := st.session_state.pop("github_connection_error", None):
    st.sidebar.error(error)

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

st.markdown(
    f"""
    <div class="impact-hero">
      <div class="eyebrow">SOFTWARE CHANGE INTELLIGENCE</div>
      <h1>ImpactLens</h1>
      <p>Understand the evidence around a change before it reaches production.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption(f"Working repository: `{repository_id or 'not selected'}`")

if workflow == "Ask the repository":
    st.subheader("Ask the repository")
    st.write("Search source, tests, architecture notes, and incidents. Answers include the retrieved files.")
    question = st.text_area(
        "Your question",
        placeholder="How does the RAG pipeline retrieve and assemble context?",
        height=110,
        label_visibility="collapsed",
    )
    if st.button("Search evidence", type="primary") and question.strip():
        try:
            result = post("/rag/query", {"repository_id": repository_id, "question": question})
            if result["abstained"]:
                st.warning("Not enough repository evidence was found for this question.")
            st.markdown("#### Simple-English summary")
            st.info(result["answer"])
            if result["citation_validation"]["supported"]:
                st.caption("Source sentences selected from retrieved evidence · citations validated")
            else:
                st.warning("Some summary citations could not be matched to the retrieved evidence.")
            st.markdown("#### Retrieved sources")
            render_evidence(result["evidence"])
        except Exception as exc:
            show_api_error(exc)

elif workflow == "Analyze a PR":
    st.subheader("PR impact review")
    st.write("Use a pull request title and description to retrieve related code, tests, and engineering notes.")
    with st.container(border=True):
        pr_number = st.text_input("Pull request number", "1")
        title = st.text_input("Pull request title")
        description = st.text_area("Description and change summary", height=120)
        analyze_clicked = st.button("Build impact report", type="primary")
    st.caption("Prototype scope: this form does not fetch a live PR diff from GitHub.")
    if analyze_clicked:
        try:
            result = post("/prs/analyze", {
                "repository_id": repository_id,
                "pull_request_number": pr_number,
                "title": title,
                "description": description,
            })
            st.markdown("#### Potential impact")
            st.info(result["summary"])
            left, right = st.columns(2)
            with left:
                st.markdown("#### Test evidence")
                if result["tests"]:
                    for test_path in result["tests"]:
                        st.write(f"`{test_path}`")
                else:
                    st.caption("No related test files were retrieved.")
            with right:
                st.markdown("#### Risk model")
                st.write(result["risk"]["reason"])
            st.markdown("#### Supporting evidence")
            render_evidence(result["evidence"])
            st.markdown("#### Uncertainties")
            for uncertainty in result["uncertainties"]:
                st.write(f"- {uncertainty}")
        except Exception as exc:
            show_api_error(exc)

else:
    st.subheader("Incident investigation")
    st.write("Find related historical records and components. Similarity is a lead, not proof of root cause.")
    description = st.text_area(
        "Incident description or stack trace",
        placeholder="Paste an error, stack trace, or concise incident summary.",
        height=150,
        label_visibility="collapsed",
    )
    if st.button("Find related evidence", type="primary") and description.strip():
        try:
            result = post("/incidents/investigate", {
                "repository_id": repository_id,
                "description": description,
            })
            st.markdown("#### Investigation status")
            if result["status"] == "insufficient_evidence":
                st.warning("No supporting repository evidence was found.")
            else:
                st.info("Retrieved similarities are hypotheses to investigate, not confirmed causes.")
            st.markdown("#### Possible hypotheses")
            for hypothesis in result["hypotheses"]:
                st.write(f"- {hypothesis}")
            st.markdown("#### Suggested investigation")
            for step in result["suggested_steps"]:
                st.write(f"- {step}")
            st.markdown("#### Related evidence")
            render_evidence(result["evidence"])
        except Exception as exc:
            show_api_error(exc)
