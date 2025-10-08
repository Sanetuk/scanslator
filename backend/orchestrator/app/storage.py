from __future__ import annotations
from app.shared.status import JobStatus

import logging
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterator, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


_DEFAULT_DB_URL = "sqlite:///orchestrator.db"
_DEFAULT_RETRIES = 10
_DEFAULT_BACKOFF_SECONDS = 1.0

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorJob:
    job_id: str
    status: JobStatus
    submitted_at: datetime
    updated_at: datetime
    detail: Optional[str] = None
    artefacts: Dict[str, str] = field(default_factory=dict)


@dataclass
class JobEventRecord:
    status: JobStatus
    detail: Optional[str]
    created_at: datetime


class Base(DeclarativeBase):
    pass


class JobModel(Base):
    __tablename__ = "jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    artefacts: Mapped[Dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)


class JobEventModel(Base):
    __tablename__ = "job_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(64), ForeignKey("jobs.job_id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)


class SQLAlchemyJobStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @contextmanager
    def _session(self) -> Iterator[Session]:
        with Session(self._engine, future=True) as session:
            yield session

    def _append_event(self, session: Session, job_id: str, status: JobStatus, detail: Optional[str], created_at: Optional[datetime] = None) -> None:
        event = JobEventModel(
            job_id=job_id,
            status=status.value,
            detail=detail,
            created_at=created_at or datetime.utcnow(),
        )
        session.add(event)

    def create(self, job: OrchestratorJob) -> OrchestratorJob:
        with self._session() as session:
            model = JobModel(
                job_id=job.job_id,
                status=job.status.value,
                detail=job.detail,
                submitted_at=job.submitted_at,
                updated_at=job.updated_at,
                artefacts=dict(job.artefacts),
            )
            session.add(model)
            session.flush()
            self._append_event(session, job.job_id, job.status, job.detail, created_at=job.submitted_at)
            session.commit()
        return job

    def get(self, job_id: str) -> Optional[OrchestratorJob]:
        with self._session() as session:
            model = session.get(JobModel, job_id)
            if not model:
                return None
            return self._to_job(model)

    def history(self, job_id: str) -> List[JobEventRecord]:
        with self._session() as session:
            rows = (
                session.query(JobEventModel)
                .filter(JobEventModel.job_id == job_id)
                .order_by(JobEventModel.created_at.asc(), JobEventModel.id.asc())
                .all()
            )
            return [
                JobEventRecord(
                    status=JobStatus(row.status),
                    detail=row.detail,
                    created_at=row.created_at,
                )
                for row in rows
            ]

    def update_status(self, job_id: str, status: JobStatus, detail: Optional[str] = None) -> Optional[OrchestratorJob]:
        with self._session() as session:
            model = session.get(JobModel, job_id)
            if not model:
                return None
            model.status = status.value
            model.detail = detail
            model.updated_at = datetime.utcnow()
            self._append_event(session, job_id, status, detail, created_at=model.updated_at)
            session.commit()
            session.refresh(model)
            return self._to_job(model)

    def set_artefact(self, job_id: str, name: str, uri: str) -> Optional[OrchestratorJob]:
        with self._session() as session:
            model = session.get(JobModel, job_id)
            if not model:
                return None
            artefacts = dict(model.artefacts or {})
            artefacts[name] = uri
            model.artefacts = artefacts
            model.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(model)
            return self._to_job(model)

    @staticmethod
    def _to_job(model: JobModel) -> OrchestratorJob:
        artefacts = dict(model.artefacts or {})
        return OrchestratorJob(
            job_id=model.job_id,
            status=JobStatus(model.status),
            detail=model.detail,
            submitted_at=model.submitted_at,
            updated_at=model.updated_at,
            artefacts=artefacts,
        )


def _create_engine() -> Engine:
    db_url = os.getenv("ORCHESTRATOR_DATABASE_URL", _DEFAULT_DB_URL)
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    retries = int(os.getenv("ORCHESTRATOR_DB_CONNECT_RETRIES", str(_DEFAULT_RETRIES)))
    backoff = float(os.getenv("ORCHESTRATOR_DB_CONNECT_BACKOFF", str(_DEFAULT_BACKOFF_SECONDS)))

    engine = create_engine(db_url, future=True, pool_pre_ping=True, connect_args=connect_args)

    if db_url.startswith("sqlite"):
        return engine

    attempt = 0
    while True:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            break
        except OperationalError as exc:  # pragma: no cover - requires Postgres downtime
            attempt += 1
            if attempt > retries:
                logger.error("Failed to connect to job store after %s attempts", retries)
                raise exc
            sleep_time = backoff * attempt
            logger.warning(
                "Database not ready (attempt %s/%s): %s. Retrying in %.1fs",
                attempt,
                retries,
                exc,
                sleep_time,
            )
            time.sleep(sleep_time)

    return engine




_engine: Engine | None = None
_store: SQLAlchemyJobStore | None = None

def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine

def get_store() -> SQLAlchemyJobStore:
    global _store
    if _store is None:
        _store = SQLAlchemyJobStore(get_engine())
    return _store



