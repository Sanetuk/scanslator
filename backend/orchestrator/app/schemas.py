from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.engine.models import JobStatus


class SourceType(str, Enum):
    PDF = "pdf"
    IMAGE = "image"
    RAW_TEXT = "raw_text"


class JobCreateRequest(BaseModel):
    source_type: SourceType
    source_uri: Optional[str] = Field(
        None,
        description="Location of the uploaded file. Direct upload flow will populate this post-ingest.",
    )
    original_filename: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus
    submitted_at: datetime


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    detail: Optional[str] = None
    submitted_at: datetime
    updated_at: datetime


class JobResultResponse(BaseModel):
    job_id: str
    status: JobStatus
    translated_text_uri: Optional[str] = None
    artefacts: Dict[str, str] = Field(default_factory=dict)


class JobCancelResponse(BaseModel):
    job_id: str
    status: JobStatus
    cancelled_at: datetime
