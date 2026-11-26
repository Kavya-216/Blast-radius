# API

Start with `uvicorn app.main:app --reload`.

- `GET /health`
- `POST /repositories` register `{repository_id, local_path, remote_url}`
- `POST /repositories/{repository_id}/index`
- `GET /repositories/{repository_id}/retrieve?query=...&limit=10`
- `POST /rag/query` `{repository_id, question}`
- `POST /prs/analyze` `{repository_id, pull_request_number, title, description}`
- `POST /incidents/investigate` `{repository_id, description}`
- `POST /webhooks/github` requires GitHub HMAC header and configured secret.

For connected GitHub repositories, `/prs/analyze` fetches the requested diff read-only. The response includes changed-file metadata and a bounded diff evidence item; local repositories use the supplied title and description without fetching GitHub data.
