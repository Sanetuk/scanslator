from __future__ import annotations

import json
import mimetypes
import os
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from .. import schemas
from app.shared.status import JobStatus
from ..constants import CANCEL_STREAM, READY_STREAM
from ..queue import queue
from ..storage import JobEventRecord, OrchestratorJob, get_store

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _serialize_history(events: List[JobEventRecord]) -> List[schemas.JobEvent]:
    return [
        schemas.JobEvent(status=event.status, detail=event.detail, created_at=event.created_at)
        for event in events
    ]


def _job_status_response(job: OrchestratorJob) -> schemas.JobStatusResponse:
    store = get_store()
    history = store.history(job.job_id)
    return schemas.JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        detail=job.detail,
        submitted_at=job.submitted_at,
        updated_at=job.updated_at,
        history=_serialize_history(history),
    )


@router.post("", response_model=schemas.JobCreateResponse, status_code=202)
async def create_job(request: schemas.JobCreateRequest) -> schemas.JobCreateResponse:
    job_id = str(uuid.uuid4())
    now = datetime.utcnow()
    store = get_store()
    store.create(
        OrchestratorJob(
            job_id=job_id,
            status=JobStatus.PENDING,
            submitted_at=now,
            updated_at=now,
        )
    )
    payload = {
        "job_id": job_id,
        "source_type": request.source_type.value,
        "source_uri": request.source_uri,
        "original_filename": request.original_filename,
        "options": request.options,
        "submitted_at": now.isoformat(),
    }
    await queue.publish(READY_STREAM, payload)
    return schemas.JobCreateResponse(job_id=job_id, status=JobStatus.PENDING, submitted_at=now)


@router.get("/{job_id}", response_model=schemas.JobStatusResponse)
def get_job_status(job_id: str) -> schemas.JobStatusResponse:
    store = get_store()
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_status_response(job)


@router.get("/{job_id}/timeline", response_model=list[schemas.JobEvent])
def get_job_timeline(job_id: str) -> list[schemas.JobEvent]:
    store = get_store()
    if not store.get(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return _serialize_history(store.history(job_id))


@router.get("/{job_id}/result", response_model=schemas.JobResultResponse)
def get_job_result(job_id: str) -> schemas.JobResultResponse:
    store = get_store()
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


@router.get("/{job_id}/artefacts/{name}")
def get_job_artefact(job_id: str, name: str):
    store = get_store()
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    artefact = job.artefacts.get(name)
    if artefact is None:
        raise HTTPException(status_code=404, detail="Artefact not found")

    if isinstance(artefact, str) and os.path.isfile(artefact):
        media_type, _ = mimetypes.guess_type(artefact)
        return FileResponse(
            path=artefact,
            filename=os.path.basename(artefact),
            media_type=media_type or "application/octet-stream",
        )

    if isinstance(artefact, str):
        try:
            return JSONResponse(json.loads(artefact))
        except json.JSONDecodeError:
            return PlainTextResponse(artefact, media_type="text/plain")

    return JSONResponse(artefact)


@router.post("/{job_id}/cancel", response_model=schemas.JobCancelResponse)
async def cancel_job(job_id: str) -> schemas.JobCancelResponse:
    store = get_store()
    job = store.update_status(job_id, JobStatus.CANCELLED)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await queue.publish(CANCEL_STREAM, {"job_id": job_id})
    return schemas.JobCancelResponse(job_id=job.job_id, status=job.status, cancelled_at=job.updated_at)


@router.post("/status")
async def update_job_status(payload: schemas.JobStatusPatch) -> dict[str, str]:
    store = get_store()
    job = store.update_status(payload.job_id, payload.status, payload.detail)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if payload.artefacts:
        for name, uri in payload.artefacts.items():
            store.set_artefact(payload.job_id, name, uri)
    return {"status": "updated"}
