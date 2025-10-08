import logging
from pathlib import Path
from typing import Iterable

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

logger = logging.getLogger(__name__)

_FONT_FILENAME = "NotoSansKR-VariableFont_wght.ttf"


def _font_search_paths() -> Iterable[Path]:
    base = Path(__file__).resolve()
    candidates = [
        base.parents[2] / "fonts",  # /app/app/fonts (historical layout)
        base.parents[3] / "fonts",  # /app/fonts (current docker layout)
        Path.cwd() / "fonts",
    ]
    seen = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        yield candidate


def _locate_font() -> Path:
    for directory in _font_search_paths():
        font_path = directory / _FONT_FILENAME
        if font_path.exists():
            return font_path
    raise FileNotFoundError(f"Unable to locate {_FONT_FILENAME} in known font directories")


def create_pdf_from_text(text: str, output_path: str) -> None:
    font_path = _locate_font()
    try:
        pdfmetrics.registerFont(TTFont("NotoSansKR", str(font_path)))
    except Exception as exc:
        logger.error("Failed to register font %s: %s", font_path, exc)
        raise ValueError(f"Failed to register font: {exc}") from exc

    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Translated Document", styles["h1"]))
    story.append(Spacer(1, 0.2 * inch))

    body_style = styles["Normal"]
    body_style.fontName = "NotoSansKR"
    body_style.leading = 14

    for line in text.split("\n"):
        story.append(Paragraph(line, body_style))

    doc.build(story)
    logger.info("PDF created at: %s", output_path)
