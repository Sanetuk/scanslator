from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

DEFAULT_ALLOWED_ORIGINS: tuple[str, ...] = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://192.168.10.31:5173",
)

_DEFAULT_UPLOAD_DIR = Path("uploads")
_DEFAULT_MAX_UPLOAD_BYTES = 1024 * 1024 * 1024  # 1GB


def _split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _deduplicate(items: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    deduped: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


class UploadSettings(BaseModel):
    directory: Path = Field(default=_DEFAULT_UPLOAD_DIR)
    max_size_bytes: int = Field(default=_DEFAULT_MAX_UPLOAD_BYTES, ge=1)

    @property
    def absolute_directory(self) -> Path:
        return self.directory.resolve()

    def ensure_directory(self) -> None:
        self.absolute_directory.mkdir(parents=True, exist_ok=True)

    def path_for(self, filename: str) -> Path:
        return self.absolute_directory / filename


class OrchestratorSettings(BaseModel):
    base_url: Optional[str] = None
    timeout_seconds: float = Field(default=30.0, gt=0)


class Settings(BaseModel):
    upload: UploadSettings = Field(default_factory=UploadSettings)
    orchestrator: OrchestratorSettings = Field(default_factory=OrchestratorSettings)
    extra_allowed_origins: List[str] = Field(default_factory=list)
    render_external_url: Optional[str] = None

    @property
    def allowed_origins(self) -> List[str]:
        base = list(DEFAULT_ALLOWED_ORIGINS)
        if self.render_external_url:
            base.append(self.render_external_url)
        base.extend(self.extra_allowed_origins)
        return _deduplicate(base)

    @classmethod
    def load(cls) -> "Settings":
        upload_dir_value = os.environ.get("UPLOAD_DIR")
        upload_dir = Path(upload_dir_value) if upload_dir_value else _DEFAULT_UPLOAD_DIR

        max_upload_value = os.environ.get("MAX_UPLOAD_SIZE_BYTES")
        max_upload = int(max_upload_value) if max_upload_value else _DEFAULT_MAX_UPLOAD_BYTES

        timeout_value = os.environ.get("ORCHESTRATOR_TIMEOUT")
        timeout = float(timeout_value) if timeout_value else 30.0

        extra_origins: List[str] = []
        single_origin = os.environ.get("ALLOWED_FRONTEND_ORIGIN")
        if single_origin:
            extra_origins.append(single_origin)
        csv_origins = os.environ.get("ALLOWED_FRONTEND_ORIGINS")
        if csv_origins:
            extra_origins.extend(_split_csv(csv_origins))

        settings = cls(
            upload=UploadSettings(directory=upload_dir, max_size_bytes=max_upload),
            orchestrator=OrchestratorSettings(
                base_url=os.environ.get("ORCHESTRATOR_BASE_URL"),
                timeout_seconds=timeout,
            ),
            extra_allowed_origins=extra_origins,
            render_external_url=os.environ.get("RENDER_EXTERNAL_URL"),
        )
        settings.upload.ensure_directory()
        return settings


settings = Settings.load()
