from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.shared.status import JobStatus


class UploadResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    submitted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    detail: Optional[str] = None


class JobEvent(BaseModel):
    status: JobStatus
    created_at: datetime
    detail: Optional[str] = None


class JobTimelineResponse(JobStatusResponse):
    history: List[JobEvent] = Field(default_factory=list)


class JobResultResponse(BaseModel):
    job_id: str
    status: Optional[JobStatus] = None
    translated_text: Optional[str] = None
    original_images: List[str] = Field(default_factory=list)
    artefacts: Dict[str, str] = Field(default_factory=dict)
