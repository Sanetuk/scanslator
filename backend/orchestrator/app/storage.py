from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

from app.engine.models import JobStatus


@dataclass
class OrchestratorJob:
    job_id: str
    status: JobStatus
    submitted_at: datetime
    updated_at: datetime
    detail: Optional[str] = None
    artefacts: Dict[str, str] = field(default_factory=dict)


class InMemoryJobStore:
    def __init__(self) -> None:
        self._jobs: Dict[str, OrchestratorJob] = {}

    def create(self, job: OrchestratorJob) -> OrchestratorJob:
        self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> Optional[OrchestratorJob]:
        return self._jobs.get(job_id)

    def update_status(self, job_id: str, status: JobStatus, detail: Optional[str] = None) -> Optional[OrchestratorJob]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job.status = status
        job.updated_at = datetime.utcnow()
        job.detail = detail
        return job

    def set_artefact(self, job_id: str, name: str, uri: str) -> Optional[OrchestratorJob]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job.artefacts[name] = uri
        job.updated_at = datetime.utcnow()
        return job


store = InMemoryJobStore()
