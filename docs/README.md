# Documentation Overview

This folder contains the working design artefacts for the Lao-Korean translator project.

- `PRD.md` ? Product requirements captured for v1.1, now reflecting the modular engine and planned orchestrator service.
- `PROJECT_PLAN.md` ? Phased roadmap, including the upcoming orchestrator build-out and documentation tasks.
- `orchestrator-worker-architecture.md` ? Interaction model between orchestrator and worker processes, with notes about the shared translation engine package (`backend/app/engine/`).

The FastAPI backend currently instantiates the `TranslationPipeline` directly. As the dedicated orchestrator service is scaffolded, update these documents with queue configuration, deployment topology, and migration steps.
