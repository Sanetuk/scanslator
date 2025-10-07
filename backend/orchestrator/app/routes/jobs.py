from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.engine.models import JobStatus
from orchestrator.app import schemas
from orchestrator.app.storage import OrchestratorJob, store

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=schemas.JobCreateResponse, status_code=202)
def create_job(request: schemas.JobCreateRequest) -> schemas.JobCreateResponse:
    job_id = str(uuid.uuid4())
    now = datetime.utcnow()
    store.create(
        OrchestratorJob(
            job_id=job_id,
            status=JobStatus.PENDING,
            submitted_at=now,
            updated_at=now,
        )
    )
    # TODO: enqueue work item (source upload metadata, options) to message bus.
    return schemas.JobCreateResponse(job_id=job_id, status=JobStatus.PENDING, submitted_at=now)


@router.get("/{job_id}", response_model=schemas.JobStatusResponse)
def get_job_status(job_id: str) -> schemas.JobStatusResponse:
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return schemas.JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        detail=job.detail,
        submitted_at=job.submitted_at,
        updated_at=job.updated_at,
    )


@router.get("/{job_id}/result", response_model=schemas.JobResultResponse)
def get_job_result(job_id: str) -> schemas.JobResultResponse:
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in {JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.CANCELLED}:
        raise HTTPException(status_code=409, detail="Job not finished")
    return schemas.JobResultResponse(
        job_id=job.job_id,
        status=job.status,
        translated_text_uri=job.artefacts.get("translated_text"),
        artefacts=dict(job.artefacts),
    )


@router.post("/{job_id}/cancel", response_model=schemas.JobCancelResponse)
def cancel_job(job_id: str) -> schemas.JobCancelResponse:
    job = store.update_status(job_id, JobStatus.CANCELLED)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # TODO: publish cancellation message so workers can stop processing.
    return schemas.JobCancelResponse(job_id=job.job_id, status=job.status, cancelled_at=job.updated_at)
