import os
import uuid
import pytesseract
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file
print(f"DEBUG: GEMINI_API_KEY loaded: {os.environ.get('GEMINI_API_KEY')}")
from pdf2image import convert_from_path

pytesseract.pytesseract.tesseract_cmd = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tesseract', 'tesseract.exe'))
from PIL import Image
import google.generativeai as genai
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from enum import Enum
from prompts import INITIAL_TRANSLATION_PROMPT, REFINEMENT_PROMPT
import base64
import io
import logging

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://192.168.10.31:5173",
]
render_external_url = os.environ.get('RENDER_EXTERNAL_URL')
if render_external_url:
    origins.append(render_external_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini API
# IMPORTANT: Replace with your actual API key or set it as an environment variable
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set. The service cannot start without it.")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def _convert_file_to_images(file_path: str, file_type: str, task_id: str) -> list[Image.Image]:
    try:
        images = []
        if file_type == 'application/pdf':
            poppler_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'poppler-24.08.0', 'Library', 'bin'))
            images = convert_from_path(file_path, poppler_path=poppler_path)
        else:
            images = [Image.open(file_path)]
        logger.info(f"[Task {task_id}] Converted file to {len(images)} image(s).")
        return images
    except Exception as e:
        raise ValueError(f"Failed to convert file to image: {e}")

def _save_images_as_base64(images: list[Image.Image], task_id: str) -> list[str]:
    base64_images = []
    for image in images:
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        base64_images.append(base64.b64encode(buffered.getvalue()).decode('utf-8'))
    logger.info(f"[Task {task_id}] Converted {len(images)} image(s) to base64.")
    return base64_images

def _perform_ocr(images: list[Image.Image], task_id: str) -> str:
    try:
        extracted_text = ""
        for i, image in enumerate(images):
            extracted_text += pytesseract.image_to_string(image, lang='lao')
            logger.info(f"[Task {task_id}] OCR completed for image {i+1}.")
        if not extracted_text.strip():
            raise ValueError("OCR failed to extract any text.")
        return extracted_text
    except Exception as e:
        raise ValueError(f"OCR process failed: {e}")

def _translate_text_with_gemini(extracted_text: str, task_id: str) -> str:
    # Define a maximum chunk size for input text (in characters)
    # This is a heuristic to avoid hitting output token limits.
    # 20,000 characters is a conservative estimate, assuming ~4 chars/token and 2x expansion.
    MAX_INPUT_CHUNK_CHARS = 20000 

    translated_chunks = []
    current_pos = 0

    while current_pos < len(extracted_text):
        logger.info(f"[Task {task_id}] Chunking: current_pos={current_pos}/{len(extracted_text)}")
        
        # Determine the maximum possible end for this chunk
        max_chunk_end = min(current_pos + MAX_INPUT_CHUNK_CHARS, len(extracted_text))
        
        # Try to find a natural break point within this maximum chunk
        break_point = -1
        
        # Search for double newline from max_chunk_end backwards to current_pos
        double_newline_idx = extracted_text.rfind('\n\n', current_pos, max_chunk_end)
        if double_newline_idx != -1:
            break_point = double_newline_idx + 2 # Include the newlines in the break
        
        # If no double newline, search for a period
        if break_point == -1:
            period_idx = extracted_text.rfind('.', current_pos, max_chunk_end)
            if period_idx != -1:
                break_point = period_idx + 1 # Include the period in the break

        # If no natural break found, or if the natural break is too close to current_pos
        # (meaning the chunk would be empty or very small), then just take the full max_chunk_end.
        # Also, ensure break_point is at least current_pos + 1 if there's still text.
        if break_point <= current_pos or break_point == -1:
            break_point = max_chunk_end
        
        # Ensure break_point is at least current_pos + 1 if there's text remaining
        if break_point == current_pos and current_pos < len(extracted_text):
            break_point = min(current_pos + 1, len(extracted_text))

        logger.info(f"[Task {task_id}] Chunking: max_chunk_end={max_chunk_end}, break_point={break_point}")
        chunk = extracted_text[current_pos:break_point]
        
        if not chunk.strip(): # If the chunk is empty or only whitespace
            logger.info(f"[Task {task_id}] Skipping empty/whitespace chunk at current_pos={current_pos}")
            current_pos = break_point # Advance current_pos past this empty section
            continue

        try:
            logger.info(f"[Task {task_id}] Translating chunk (length: {len(chunk)} characters)...")
            prompt = INITIAL_TRANSLATION_PROMPT.format(extracted_text=chunk)
            response = model.generate_content(prompt)
            
            if not response.candidates:
                logger.error(f"[Task {task_id}] Initial translation failed for chunk: No candidates returned.")
                if response.prompt_feedback:
                    logger.error(f"[Task {task_id}] Prompt feedback: {response.prompt_feedback}")
                if response.usage_metadata:
                    logger.error(f"[Task {task_id}] Usage metadata: {response.usage_metadata}")
                raise ValueError("Gemini API initial translation failed for chunk: No candidates returned.")

            translated_chunks.append(response.text)
            logger.info(f"[Task {task_id}] Chunk translation successful. Translated text length: {len(response.text)} characters.")

        except Exception as e:
            logger.error(f"[Task {task_id}] Gemini API translation failed for chunk: {e}")
            raise ValueError(f"Gemini API translation failed for chunk: {e}")
        
        current_pos = break_point
        if current_pos == len(extracted_text) and break_point < len(extracted_text): # Handle case where last chunk was a partial break
            current_pos = len(extracted_text)

    full_translated_text = "".join(translated_chunks)
    logger.info(f"[Task {task_id}] All chunks translated. Total translated text length: {len(full_translated_text)} characters.")
    logger.info(f"[Task {task_id}] Length of text for refinement: {len(full_translated_text)} characters.")

    # Apply refinement to the full translated text
    try:
        refinement_prompt = REFINEMENT_PROMPT.format(translated_text=full_translated_text)
        logger.info(f"[Task {task_id}] Calling Gemini API for refinement...")
        refinement_response = model.generate_content(refinement_prompt)
        logger.info(f"[Task {task_id}] Gemini API refinement response received.")
        
        if not refinement_response.candidates:
            logger.error(f"[Task {task_id}] Refinement failed: No candidates returned.")
            if refinement_response.prompt_feedback:
                logger.error(f"[Task {task_id}] Refinement prompt feedback: {refinement_response.prompt_feedback}")
            if refinement_response.usage_metadata:
                logger.error(f"[Task {task_id}] Refinement usage metadata: {refinement_response.usage_metadata}")
            raise ValueError("Gemini API refinement failed: No candidates returned.")

        translated_text = refinement_response.text
        logger.info(f"[Task {task_id}] Translation refinement successful. Refined text length: {len(translated_text)} characters.")
        
        return translated_text
    except Exception as e:
        raise ValueError(f"Gemini API refinement failed: {e}")

def _create_pdf_from_text(text: str, output_path: str):
    # Register Korean font
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fonts', 'NotoSansKR-VariableFont_wght.ttf'))
    try:
        pdfmetrics.registerFont(TTFont('NotoSansKR', font_path))
    except Exception as e:
        logger.error(f"Failed to register font {font_path}: {e}")
        raise ValueError(f"Failed to register font: {e}")

    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Add a title
    story.append(Paragraph("Translated Document", styles['h1']))
    story.append(Spacer(1, 0.2 * inch))

    # Use the registered Korean font for body text
    body_style = styles['Normal']
    body_style.fontName = 'NotoSansKR'
    body_style.leading = 14 # Line spacing

    # Preserve line breaks by splitting the text and adding each line as a paragraph
    for line in text.split('\n'):
        story.append(Paragraph(line, body_style))

    doc.build(story)
    logger.info(f"PDF created at: {output_path}")

class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"

class TranslationJob(BaseModel):
    task_id: str
    status: JobStatus
    original_images: list[str] | None = None
    translated_text: str | None = None
    detail: str | None = None

jobs = {}

def process_file(task_id: str, file_path: str, file_type: str):
    jobs[task_id].status = JobStatus.PROCESSING
    logger.info(f"[Task {task_id}] Starting processing for file: {file_path}")

    try:
        images = _convert_file_to_images(file_path, file_type, task_id)
        base64_images = _save_images_as_base64(images, task_id)
        jobs[task_id].original_images = base64_images
        extracted_text = _perform_ocr(images, task_id)
        translated_text = _translate_text_with_gemini(extracted_text, task_id)

        # Step 5: Finalize job
        jobs[task_id].status = JobStatus.COMPLETE
        jobs[task_id].translated_text = translated_text
        logger.info(f"[Task {task_id}] Processing complete.")

    except Exception as e:
        error_message = str(e)
        logger.error(f"[Task {task_id}] Processing failed: {error_message}")
        jobs[task_id].status = JobStatus.FAILED
        jobs[task_id].detail = error_message

@app.post("/upload/")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    task_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{task_id}_{file.filename}")

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    jobs[task_id] = TranslationJob(task_id=task_id, status=JobStatus.PENDING)
    
    background_tasks.add_task(process_file, task_id, file_path, file.content_type)

    return {"task_id": task_id}


@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    job = jobs.get(task_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": job.status, "detail": job.detail}

@app.get("/api/result/{task_id}")
async def get_result(task_id: str, format: str | None = None):
    job = jobs.get(task_id)
    if not job or job.status != JobStatus.COMPLETE:
        raise HTTPException(status_code=404, detail="Result not available")

    if format == "pdf":
        if not job.translated_text:
            raise HTTPException(status_code=404, detail="Translated text not available for PDF conversion.")
        
        pdf_filename = f"translation_{task_id}.pdf"
        pdf_path = os.path.join(UPLOAD_DIR, pdf_filename)
        
        try:
            _create_pdf_from_text(job.translated_text, pdf_path)
            return FileResponse(path=pdf_path, filename=pdf_filename, media_type="application/pdf")
        except Exception as e:
            logger.error(f"Failed to create PDF for task {task_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {e}")

    return {
        "original_images": job.original_images,
        "translated_text": job.translated_text
    }

@app.get("/api/list_models")
async def list_models():
    try:
        models = [m.name for m in genai.list_models()]
        return {"available_models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {e}")