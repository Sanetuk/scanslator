import json
import os
import uuid
from typing import Any, Dict

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.requests import Request

from app.engine.services.export import create_pdf_from_text
from app.settings import settings


import logging


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LargeUploadRequest(Request):
    async def _get_form(
        self,
        *,
        max_files: int | float = 1000,
        max_fields: int | float = 1000,
        max_part_size: int = 1024 * 1024,
    ):
        adjusted_part_size = max_part_size
        if max_part_size == 1024 * 1024:
            adjusted_part_size = settings.upload.max_size_bytes
        return await super()._get_form(
            max_files=max_files,
            max_fields=max_fields,
            max_part_size=adjusted_part_size,
        )


app = FastAPI(request_class=LargeUploadRequest)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.on_event('startup')
async def _startup() -> None:
    if settings.orchestrator.base_url:
        app.state.http_client = httpx.AsyncClient(
            base_url=settings.orchestrator.base_url,
            timeout=settings.orchestrator.timeout_seconds,
        )
    else:
        app.state.http_client = None


@app.on_event('shutdown')
async def _shutdown() -> None:
    client: httpx.AsyncClient | None = getattr(app.state, 'http_client', None)
    if client:
        await client.aclose()


def _get_http_client() -> httpx.AsyncClient:
    client: httpx.AsyncClient | None = getattr(app.state, 'http_client', None)
    if client is None:
        raise HTTPException(status_code=503, detail='Orchestrator service is not configured.')
    return client

def _determine_source_type(content_type: str | None) -> str:
    if not content_type:
        return 'raw_text'
    if 'pdf' in content_type:
        return 'pdf'
    if content_type.startswith('image/'):
        return 'image'
    return 'raw_text'


async def _post_orchestrator(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    client = _get_http_client()
    try:
        response = await client.post(path, json=payload)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:  # pragma: no cover - network path
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
    except httpx.RequestError as exc:  # pragma: no cover - network path
        raise HTTPException(status_code=503, detail=f'Failed to reach orchestrator: {exc}')


async def _get_orchestrator(path: str) -> Dict[str, Any]:
    client = _get_http_client()
    try:
        response = await client.get(path)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail=f'Failed to reach orchestrator: {exc}')


def _sanitize_filename(filename: str | None) -> str:
    if not filename:
        return "upload"
    return os.path.basename(filename)


async def _save_upload_to_disk(file: UploadFile, destination: str) -> None:
    chunk_size = 4 * 1024 * 1024  # 4MB
    total_bytes = 0
    try:
        with open(destination, 'wb') as buffer:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > settings.upload.max_size_bytes:
                    raise HTTPException(status_code=413, detail='Uploaded file exceeds allowed size.')
                buffer.write(chunk)
    except Exception:
        try:
            os.remove(destination)
        except FileNotFoundError:
            pass
        raise
    finally:
        await file.close()


@app.post('/upload/')
async def upload_file(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    safe_filename = _sanitize_filename(file.filename)
    file_path = str(settings.upload.path_for(f'{job_id}_{safe_filename}'))

    await _save_upload_to_disk(file, file_path)

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
        pdf_path = str(settings.upload.path_for(pdf_filename))
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
