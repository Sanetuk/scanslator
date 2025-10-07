import logging
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

logger = logging.getLogger(__name__)


def create_pdf_from_text(text: str, output_path: str) -> None:
    fonts_dir = Path(__file__).resolve().parents[2] / "fonts"
    font_path = fonts_dir / "NotoSansKR-VariableFont_wght.ttf"

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
