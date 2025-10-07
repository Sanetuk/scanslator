from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Optional

from pydantic import BaseModel


class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    IMAGE_CONVERSION = "IMAGE_CONVERSION"
    OCR_PROCESSING = "OCR_PROCESSING"
    TRANSLATION_PROCESSING = "TRANSLATION_PROCESSING"
    REFINEMENT_PROCESSING = "REFINEMENT_PROCESSING"
    PDF_GENERATION = "PDF_GENERATION"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


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
