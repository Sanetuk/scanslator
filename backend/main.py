import os
import uuid
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file


import google.generativeai as genai
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from prompts import INITIAL_TRANSLATION_PROMPT, REFINEMENT_PROMPT
from app.engine.models import JobStatus, TranslationJob
from app.engine.services.export import create_pdf_from_text
from app.engine.services.translation import GeminiTranslationService
from app.engine.pipeline import TranslationPipeline
import logging


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

# Dynamically add allowed frontend origin from environment variable
allowed_frontend_origin = os.environ.get('ALLOWED_FRONTEND_ORIGIN')
if allowed_frontend_origin:
    origins.append(allowed_frontend_origin)

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
translator_service = GeminiTranslationService(
    model,
    INITIAL_TRANSLATION_PROMPT,
    REFINEMENT_PROMPT,
)

pipeline = TranslationPipeline(translator_service)

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

jobs = {}


def _update_job_status(task_id: str, status: JobStatus) -> None:
    job = jobs.get(task_id)
    if job:
        job.status = status


def process_file(task_id: str, file_path: str, file_type: str):
    job = jobs[task_id]
    _update_job_status(task_id, JobStatus.PROCESSING)
    logger.info(f"[Task {task_id}] Starting processing for file: {file_path}")

    try:
        result = pipeline.run(
            task_id=task_id,
            file_path=file_path,
            file_type=file_type,
            status_callback=lambda status: _update_job_status(task_id, status),
        )
        job.original_images = result.original_images
        job.translated_text = result.translated_text
        _update_job_status(task_id, JobStatus.COMPLETE)
        logger.info(f"[Task {task_id}] Processing complete.")

    except Exception as exc:
        error_message = str(exc)
        logger.error(f"[Task {task_id}] Processing failed: {error_message}")
        job.status = JobStatus.FAILED
        job.detail = error_message
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
            create_pdf_from_text(job.translated_text, pdf_path)
            return FileResponse(path=pdf_path, filename=pdf_filename, media_type="application/pdf")
        except Exception as e:
            logger.error(f"Failed to create PDF for task {task_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {e}")

    return {
        "original_images": job.original_images,
        "translated_text": job.translated_text
    }

@app.get("/api/list_models")
def list_models():
    try:
        models = [m.name for m in genai.list_models()]
        return {"available_models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {e}")


