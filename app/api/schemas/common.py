from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    database: str
    embedding_model: str
    llm_provider: str


class RepositoryRegistration(BaseModel):
    repository_id: str = Field(min_length=1, max_length=255)
    local_path: str
    remote_url: str | None = None


class RepositoryStatus(BaseModel):
    repository_id: str
    local_path: str | None
    remote_url: str | None
    index_version: str
    status: str
