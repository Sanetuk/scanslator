from dataclasses import dataclass
from typing import Callable, List, Optional

from pydantic import BaseModel

from app.shared.status import JobStatus


class TranslationJob(BaseModel):
    task_id: str
    status: JobStatus
    original_images: Optional[List[str]] = None
    translated_text: Optional[str] = None
    detail: Optional[str] = None


StatusCallback = Callable[[JobStatus], None]


@dataclass
class PipelineResult:
    translated_text: str
    original_images: List[str]


__all__ = [
    "JobStatus",
    "TranslationJob",
    "PipelineResult",
    "StatusCallback",
]
