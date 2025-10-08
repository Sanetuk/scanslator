import base64
import io
import logging
from typing import List

import fitz  # PyMuPDF
from pdf2image import convert_from_path
from PIL import Image

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str, task_id: str) -> str:
    try:
        logger.info("[Task %s] Attempting direct text extraction from PDF.", task_id)
        doc = fitz.open(file_path)
        text = "".join(page.get_text("text") for page in doc)
        doc.close()
        if text.strip():
            logger.info(
                "[Task %s] Direct text extraction successful. Extracted %d characters.",
                task_id,
                len(text),
            )
        else:
            logger.info("[Task %s] Direct text extraction resulted in empty text.", task_id)
        return text
    except Exception as exc:  # pragma: no cover - logging path
        logger.warning("[Task %s] Direct text extraction from PDF failed: %s", task_id, exc)
        return ""


def convert_file_to_images(file_path: str, file_type: str, task_id: str) -> List[Image.Image]:
    try:
        if file_type == "application/pdf":
            images = convert_from_path(file_path)
        else:
            images = [Image.open(file_path)]
        logger.info("[Task %s] Converted file to %d image(s).", task_id, len(images))
        return images
    except Exception as exc:  # pragma: no cover - logging path
        raise ValueError(f"Failed to convert file to image: {exc}") from exc


def save_images_as_base64(images: List[Image.Image], task_id: str) -> List[str]:
    base64_images: List[str] = []
    for image in images:
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        base64_images.append(base64.b64encode(buffered.getvalue()).decode("utf-8"))
    logger.info("[Task %s] Converted %d image(s) to base64.", task_id, len(images))
    return base64_images
