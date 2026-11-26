# Deployment

Local deployment uses Uvicorn. Docker exposes port 8000. GitHub Actions runs pytest on Python 3.12.

No AWS, hosted database, production secret manager, or MLflow service is configured. Persist the SQLite directory and set environment variables when using a container.
