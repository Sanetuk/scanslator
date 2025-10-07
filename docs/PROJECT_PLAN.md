# Project Plan: Lao-Korean Translator

This plan tracks the evolution of the Lao-Korean Translator as it transitions from the initial monolithic MVP to a modular orchestrator/worker architecture.

## Phase 1: MVP Delivery (Completed)
- [x] FastAPI backend with `/upload`, `/api/status/{task_id}`, `/api/result/{task_id}` endpoints.
- [x] Core pipeline: PDF/image conversion, Lao OCR (Tesseract), Gemini translation, PDF export.
- [x] Vue 3 SPA with file upload, polling, translation display, and download actions.
- [x] Dockerised local environment and Render deployment guidance.

## Phase 2: UX & Data Quality Enhancements (Completed)
- [x] Preserve and display original document images next to the translation.
- [x] Add upload progress indicator and refined status messaging in the frontend.
- [x] Sanitize secret handling (no credential logging, placeholder `.env`).
- [x] Update PRD and architecture documentation to reflect current requirements.

## Phase 3: Modular Architecture (In Progress)
- [ ] Introduce an orchestrator service that accepts client jobs (`POST /jobs`, `GET /jobs/{id}`, `GET /jobs/{id}/result`, `POST /jobs/{id}/cancel`).
- [ ] Persist job metadata and artefact locations in durable storage (database + object storage).
- [ ] Establish message queue topics for job dispatch and cancellation signalling.
- [ ] Implement worker processes that consume queue messages, execute the translation engine, and report heartbeats/completions.
- [ ] Define clear engine-worker contracts (shared DTOs, error taxonomy, retry policy).

## Phase 4: Integration & Migration
- [ ] Adapt the existing frontend to call the orchestrator endpoints and handle the expanded status set.
- [ ] Provide compatibility shims or migration guides for any legacy `/upload` consumers.
- [ ] Develop end-to-end tests covering orchestrator intake, worker processing, and result retrieval.
- [ ] Document operational runbooks (worker scaling, queue management, secret rotation).

## Phase 5: Deployment & Scaling Readiness
- [ ] Set up infrastructure-as-code or deployment automation for orchestrator and worker services.
- [ ] Add observability stack (structured logging, metrics, tracing) tailored to the new architecture.
- [ ] Perform load testing with concurrent job submissions to validate queue throughput and worker capacity.
- [ ] Establish disaster-recovery procedures (snapshot strategy, job replay guidelines).

## Documentation & Communication
- [ ] Update `README.md` with orchestrator/worker setup instructions, including environment variables and queue dependencies.
- [ ] Expand developer onboarding docs: local orchestration stack, test scripts, troubleshooting guide.
- [ ] Maintain architecture notes in `docs/` (sequence diagrams, component responsibilities) as the design evolves.

## Next Immediate Actions
1. Finalise the orchestrator API design and scaffold the service.
2. Prototype a worker that wraps the existing translation pipeline as a callable engine.
3. Validate queue-based job hand-off locally before replacing the current monolithic flow.
