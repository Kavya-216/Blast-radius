from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import EMBEDDING_MODEL, LLM_PROVIDER
from app.database.connection import initialize_database
from app.api.schemas.common import HealthResponse
from app.api.routes import repositories, workflows


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    yield


app = FastAPI(
    title="ImpactLens",
    version="0.1.0",
    description="Evidence-grounded software change impact analysis.",
    lifespan=lifespan,
)
app.include_router(repositories.router)
app.include_router(workflows.router)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        database="ready",
        embedding_model=EMBEDDING_MODEL,
        llm_provider=LLM_PROVIDER,
    )
