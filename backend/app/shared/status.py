from enum import Enum
from typing import Dict


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
    CANCELLED = "CANCELLED"


STATUS_SUMMARY: Dict[JobStatus, str] = {
    JobStatus.PENDING: "Job accepted by orchestrator",
    JobStatus.PROCESSING: "Preparing translation job",
    JobStatus.IMAGE_CONVERSION: "Converting pages to images",
    JobStatus.OCR_PROCESSING: "Extracting Lao text",
    JobStatus.TRANSLATION_PROCESSING: "Translating to Korean",
    JobStatus.REFINEMENT_PROCESSING: "Refining translation output",
    JobStatus.PDF_GENERATION: "Rendering downloadable artefacts",
    JobStatus.COMPLETE: "Translation finished",
    JobStatus.FAILED: "Job failed",
    JobStatus.CANCELLED: "Job cancelled",
}


__all__ = ["JobStatus", "STATUS_SUMMARY"]
