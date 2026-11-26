from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = Path(os.getenv("IMPACTLENS_DATABASE", BASE_DIR / "data" / "impactlens.sqlite"))
CHROMA_PATH = Path(os.getenv("IMPACTLENS_CHROMA", BASE_DIR / "chroma"))
EMBEDDING_MODEL = os.getenv("IMPACTLENS_EMBEDDING_MODEL", "offline-hash-v1")
LLM_PROVIDER = os.getenv("IMPACTLENS_LLM_PROVIDER", "mock")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
