# Orchestrator and Worker Interaction Overview

## 1. High-Level Summary
- **Orchestrator**: Receives translation requests from clients (web, CLI, partners), validates them, assigns `job_id`s, persists metadata, and publishes work items to the message queue. It also enforces auth, quotas, prioritisation, retries, and cancellation policies.
- **Worker**: Pulls jobs from the queue (or accepts pushes), downloads referenced inputs, runs the translation pipeline (conversion, OCR, translation, export), uploads artefacts, and reports status back to the orchestrator.
- **Shared Services**: Object storage keeps large binaries, the job database records metadata, and the message queue transports job commands and cancellation signals.

## 2. Component Responsibilities
### Orchestrator
- Validate incoming jobs and issue unique `job_id`s.
- Persist job requests and publish compact work descriptors to `jobs.ready` (or similar) queue topics.
- Receive heartbeat, completion, failure events, and update persisted status.
- Apply operational policy: throttling, scheduling, retries, manual overrides.

### Worker
- Consume jobs when capacity is available, prefetch required input artefacts, and execute the engine pipeline.
- Emit periodic heartbeats that describe the current stage and progress percentage.
- Upload artefacts (markdown text, PDF, previews) to object storage and return their locations.
- Report failures with categorised error codes and retry hints so the orchestrator can react intelligently.

## 3. API and Messaging Contracts
| Direction | Interface | Path / Channel | Payload Highlights | Purpose |
| --------- | --------- | -------------- | ------------------ | ------- |
| Client -> Orchestrator | HTTP REST | `POST /jobs` | upload metadata, options, auth | Create job, receive `job_id` |
| Client -> Orchestrator | HTTP REST | `GET /jobs/{id}` | none | Poll job status timeline |
| Client -> Orchestrator | HTTP REST | `GET /jobs/{id}/result` | `format` query | Retrieve final artefacts |
| Client -> Orchestrator | HTTP REST | `POST /jobs/{id}/cancel` | optional reason | Request cancellation |
| Orchestrator -> Queue | Message | `jobs.ready` topic | `job_id`, input URIs, options, priority | Notify workers of executable work |
| Worker -> Orchestrator | HTTP/gRPC | `/internal/jobs/{id}/heartbeat` | stage id, percent, worker id | Progress update |
| Worker -> Orchestrator | HTTP/gRPC | `/internal/jobs/{id}/complete` | artefact URIs, summary, duration | Mark success |
| Worker -> Orchestrator | HTTP/gRPC | `/internal/jobs/{id}/fail` | error code, message, retryable flag | Mark failure |
| Orchestrator -> Queue | Message | `jobs.cancel` topic | `job_id`, cancel token | Broadcast cancellation to workers |

> **Note**: Worker-to-orchestrator calls may be implemented as REST, gRPC, or simply by writing to a status topic. The important property is having a single source of truth for state transitions.

## 4. Example Sequence
1. Client submits `POST /jobs` with file references and translation options.
2. Orchestrator persists the request, issues `job_id`, and enqueues a work descriptor on `jobs.ready`.
3. Idle worker consumes the descriptor, downloads inputs from storage, and starts the engine pipeline.
4. Worker sends periodic heartbeats (stage = `OCR_PROCESSING`, percent = 35, etc.).
5. When finished, worker uploads artefacts and calls `/internal/jobs/{id}/complete` with locations and metrics.
6. Orchestrator updates state to `SUCCEEDED`, exposing artefact links so the client can fetch them via `GET /jobs/{id}/result`.
7. If the client calls `POST /jobs/{id}/cancel`, the orchestrator publishes a `jobs.cancel` message; workers honour it and report cancellation via the failure or completion channel.

## 5. Visual Diagram
```
+-----------------+          HTTP(S)          +-----------------------+
|  Client Apps    | -----------------------> |   Orchestrator API    |
| (web / CLI / B2B)|                         |  (auth, DB, queue)     |
+-----------------+ <------ status/results --+-----------+-----------+
                                                        |
                                      enqueue jobs      |   cancel signals
                                                        v
                                             +-----------------------+
                                             |     Message Queue     |
                                             |  (jobs.ready, etc.)   |
                                             +-----------+-----------+
                                                         |
                                                         v consume
                                             +-----------------------+
                                             |        Worker         |
                                             |   (engine pipeline)   |
                                             +-----------+-----------+
                                                         |
                                                         v heartbeats/results
                                             +-----------------------+
                                             |  Orchestrator state   |
                                             |   DB & artefact map   |
                                             +-----------+-----------+
                                                         |
                                                         v artefact URIs
                                             +-----------------------+
                                             |    Object Storage     |
                                             |   (PDF / TXT / img)   |
                                             +-----------------------+
```

This markdown captures the division of responsibilities between orchestrator and worker processes, the contracts they use to exchange information, and a visual representation of how messages flow through the system. Additional operational details (authentication, retries, back-off policies) can be layered on top of this baseline design.

## 6. Translation Engine Package
- Location: `backend/app/engine/`
- Core modules:
  - `models.py`: job status enums, shared DTOs, pipeline result dataclass.
  - `services/`: ingestion, OCR, translation, and export services, each encapsulating external dependencies.
  - `pipeline.py`: `TranslationPipeline` orchestrates services, emits status callbacks, and returns artefacts.
- FastAPI currently hosts the orchestrator stub, instantiating the pipeline directly; forthcoming work will migrate job intake and state management to a dedicated orchestrator service while reusing these components.
