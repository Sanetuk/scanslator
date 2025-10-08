import logging
from typing import Optional

from app.engine.models import JobStatus, PipelineResult, StatusCallback
from app.engine.services.ingestion import (
    convert_file_to_images,
    extract_text_from_pdf,
    save_images_as_base64,
)
from app.engine.services.ocr import perform_ocr
from app.engine.services.translation import GeminiTranslationService

logger = logging.getLogger(__name__)


class TranslationPipeline:
    def __init__(self, translator: GeminiTranslationService) -> None:
        self._translator = translator

    def run(
        self,
        task_id: str,
        file_path: str,
        file_type: str,
        status_callback: Optional[StatusCallback] = None,
    ) -> PipelineResult:
        def _notify(status: JobStatus) -> None:
            if status_callback:
                status_callback(status)

        extracted_text = ""
        if file_type == "application/pdf":
            extracted_text = extract_text_from_pdf(file_path, task_id)

        _notify(JobStatus.IMAGE_CONVERSION)
        images = convert_file_to_images(file_path, file_type, task_id)
        base64_images = save_images_as_base64(images, task_id)

        _notify(JobStatus.OCR_PROCESSING)
        if not extracted_text.strip():
            logger.info("[Task %s] Using OCR pipeline for text extraction.", task_id)
            extracted_text = perform_ocr(images, task_id)
        else:
            logger.info("[Task %s] Direct text extraction succeeded; skipping OCR.", task_id)

        _notify(JobStatus.TRANSLATION_PROCESSING)

        def _notify_refinement() -> None:
            _notify(JobStatus.REFINEMENT_PROCESSING)

        translated_text = self._translator.translate(
            extracted_text,
            task_id,
            on_refinement=_notify_refinement,
        )

        return PipelineResult(
            translated_text=translated_text,
            original_images=base64_images,
        )
