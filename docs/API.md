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
