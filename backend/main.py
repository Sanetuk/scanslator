import json
import os
import uuid
from typing import Any, Dict

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.engine.services.export import create_pdf_from_text

load_dotenv()  # Load environment variables from .env file


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
    allow_methods=['*'],
    allow_headers=['*'],
)

UPLOAD_DIR = 'uploads'
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

ORCHESTRATOR_BASE_URL = os.getenv('ORCHESTRATOR_BASE_URL')
ORCHESTRATOR_TIMEOUT = float(os.getenv('ORCHESTRATOR_TIMEOUT', '30'))


def _determine_source_type(content_type: str | None) -> str:
    if not content_type:
        return 'raw_text'
    if 'pdf' in content_type:
        return 'pdf'
    if content_type.startswith('image/'):
        return 'image'
    return 'raw_text'


async def _post_orchestrator(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if not ORCHESTRATOR_BASE_URL:
        raise HTTPException(status_code=503, detail='Orchestrator service is not configured.')
    try:
        async with httpx.AsyncClient(base_url=ORCHESTRATOR_BASE_URL, timeout=ORCHESTRATOR_TIMEOUT) as client:
            response = await client.post(path, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:  # pragma: no cover - network path
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
    except httpx.RequestError as exc:  # pragma: no cover - network path
        raise HTTPException(status_code=503, detail=f'Failed to reach orchestrator: {exc}')


async def _get_orchestrator(path: str) -> Dict[str, Any]:
    if not ORCHESTRATOR_BASE_URL:
        raise HTTPException(status_code=503, detail='Orchestrator service is not configured.')
    try:
        async with httpx.AsyncClient(base_url=ORCHESTRATOR_BASE_URL, timeout=ORCHESTRATOR_TIMEOUT) as client:
            response = await client.get(path)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail=f'Failed to reach orchestrator: {exc}')


@app.post('/upload/')
async def upload_file(file: UploadFile = File(...)):
    file_contents = await file.read()
    job_id = str(uuid.uuid4())
    file_path = os.path.abspath(os.path.join(UPLOAD_DIR, f'{job_id}_{file.filename}'))

    with open(file_path, 'wb') as buffer:
        buffer.write(file_contents)

    source_type = _determine_source_type(file.content_type)
    payload = {
        'source_type': source_type,
        'source_uri': file_path,
        'original_filename': file.filename,
        'options': {'content_type': file.content_type},
    }

    orchestrator_response = await _post_orchestrator('/jobs', payload)
    return {
        'task_id': orchestrator_response.get('job_id', job_id),
        'status': orchestrator_response.get('status'),
    }


@app.get('/api/status/{task_id}')
async def get_status(task_id: str):
    data = await _get_orchestrator(f'/jobs/{task_id}')
    return {'status': data.get('status'), 'detail': data.get('detail')}


@app.get('/api/result/{task_id}')
async def get_result(task_id: str, format: str | None = None):
    data = await _get_orchestrator(f'/jobs/{task_id}/result')
    artefacts = data.get('artefacts', {})
    translated_text = artefacts.get('translated_text')
    original_images_serialized = artefacts.get('original_images')
    try:
        original_images = json.loads(original_images_serialized) if original_images_serialized else []
    except json.JSONDecodeError:
        original_images = []

    if format == 'pdf':
        if not translated_text:
            raise HTTPException(status_code=404, detail='Translated text not available for PDF conversion.')
        pdf_filename = f'translation_{task_id}.pdf'
        pdf_path = os.path.join(UPLOAD_DIR, pdf_filename)
        try:
            create_pdf_from_text(translated_text, pdf_path)
            return FileResponse(path=pdf_path, filename=pdf_filename, media_type='application/pdf')
        except Exception as exc:  # pragma: no cover - file IO path
            logger.error('Failed to create PDF for task %s: %s', task_id, exc)
            raise HTTPException(status_code=500, detail=f'Failed to generate PDF: {exc}')

    return {
        'original_images': original_images,
        'translated_text': translated_text,
    }


@app.get('/api/list_models')
def list_models():
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise HTTPException(status_code=503, detail='GEMINI_API_KEY is not configured.')
    try:
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models()]
        return {'available_models': models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to list models: {e}')


