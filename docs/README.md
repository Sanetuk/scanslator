# Documentation Overview

This folder contains the working design artefacts for the Lao-Korean translator project.

- `PRD.md` - Product requirements captured for v1.1, now reflecting the modular engine and planned orchestrator service.
- `PROJECT_PLAN.md` - Phased roadmap, including the upcoming orchestrator build-out and documentation tasks.
- `orchestrator-worker-architecture.md` - Interaction model between orchestrator and worker processes, with notes about the shared translation engine package (`backend/app/engine/`).

The FastAPI backend currently still exposes legacy `/upload` endpoints, while the new orchestrator persists jobs through SQLAlchemy (Postgres by default, SQLite fallback) and publishes work to a Redis-compatible queue abstraction. Worker code lives in `backend/worker/` and consumes the same interface; update these docs as the Redis connection and distributed deployment are finalised.


## Running Locally
- REST surface now includes GET /jobs/{id}/timeline for progress history and GET /jobs/{id}/artefacts/{name} for direct artefact retrieval.
- Orchestrator runs Alembic migrations on startup; verify lembic.ini if you change database paths.
- `docker compose up --build` now launches Redis, Postgres (with built-in health check), orchestrator (port 8001 internal), backend (legacy API proxy), worker, and the Vue frontend.
- Postgres data is stored in the `postgres-data` volume; credentials default to `orchestrator`/`orchestrator` (override with env vars as needed).
- Shared uploads directory is mounted into backend and worker (`./backend/uploads`), so queued jobs can read the files saved during upload.
- Configure `.env` for the backend (Gemini API key, etc.) and ensure `ORCHESTRATOR_BASE_URL`/`REDIS_URL` are set via compose before starting. Optional knobs: `ORCHESTRATOR_DB_CONNECT_RETRIES`/`ORCHESTRATOR_DB_CONNECT_BACKOFF` govern how long the orchestrator waits for the database to become available.
- Optional queue knobs (JOB_QUEUE_MAX_RETRIES, JOB_QUEUE_BACKOFF_BASE_SECONDS, JOB_QUEUE_ACK_TIMEOUT_MS) control retry limits and visibility timeouts for the worker.
- Worker fails fast if REDIS_URL is missing or Redis is unreachable; update queue settings before starting the stack.


