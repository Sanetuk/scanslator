from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from app.shared.status import JobStatus

from .exceptions import ApiError
from .models import JobResultResponse, JobStatusResponse, UploadResponse

_DEFAULT_TIMEOUT = 30.0


class JobsApiClient:
    """Convenience wrapper around the backend REST API."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "JobsApiClient":  # pragma: no cover - convenience
        return self

    def __exit__(self, *exc: object) -> None:  # pragma: no cover - convenience
        self.close()

    # ------------------------------------------------------------------
    def submit_job(
        self,
        file_path: str | Path,
        *,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> UploadResponse:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(path)

        detected_type = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        name = filename or path.name

        with path.open("rb") as buffer:
            files = {"file": (name, buffer, detected_type)}
            response = self._client.post("/upload/", files=files)
        data = self._json(response)
        return UploadResponse(job_id=data["task_id"], status=JobStatus(data.get("status", "PENDING")))

    def get_status(self, job_id: str) -> JobStatusResponse:
        response = self._client.get(f"/api/status/{job_id}")
        data = self._json(response)
        status_value = data.get("status", "PENDING")
        return JobStatusResponse(
            job_id=job_id,
            status=JobStatus(status_value),
            detail=data.get("detail"),
            submitted_at=data.get("submitted_at"),
            updated_at=data.get("updated_at"),
        )

    def get_result(self, job_id: str) -> JobResultResponse:
        response = self._client.get(f"/api/result/{job_id}")
        data = self._json(response)
        return JobResultResponse(
            job_id=job_id,
            status=JobStatus(data["status"]) if "status" in data else None,
            translated_text=data.get("translated_text"),
            original_images=list(data.get("original_images", [])),
            artefacts=dict(data.get("artefacts", {})),
        )

    def download_result(self, job_id: str, *, format: str, output_path: str | Path) -> Path:
        response = self._client.get(f"/api/result/{job_id}", params={"format": format})
        if response.status_code >= 400:
            raise ApiError(response.status_code, response.text)
        path = Path(output_path)
        path.write_bytes(response.content)
        return path

    # ------------------------------------------------------------------
    @staticmethod
    def _json(response: httpx.Response) -> Dict[str, Any]:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            payload: Dict[str, Any]
            try:
                payload = response.json()
            except ValueError:
                payload = {"detail": response.text}
            raise ApiError(response.status_code, payload.get("detail", exc.args[0]), payload) from exc
        try:
            return response.json()
        except ValueError as exc:
            raise ApiError(response.status_code, "Invalid JSON response") from exc
