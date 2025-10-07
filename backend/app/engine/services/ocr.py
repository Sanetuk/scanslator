import logging
from typing import List

import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


def perform_ocr(images: List[Image.Image], task_id: str) -> str:
    try:
        extracted_text = ""
        for index, image in enumerate(images, start=1):
            extracted_text += pytesseract.image_to_string(image, lang="lao")
            logger.info("[Task %s] OCR completed for image %d.", task_id, index)
        if not extracted_text.strip():
            raise ValueError("OCR failed to extract any text.")
        return extracted_text
    except Exception as exc:
        raise ValueError(f"OCR process failed: {exc}") from exc
