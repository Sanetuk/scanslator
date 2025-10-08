from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
from dataclasses import dataclass
from typing import AsyncIterator, Awaitable, Dict, Optional

import httpx
from dotenv import load_dotenv

from app.engine.factory import create_pipeline
from app.shared.status import JobStatus, STATUS_SUMMARY

load_dotenv()

class ConfigurationError(RuntimeError):
    """Raised when worker configuration is invalid."""


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigurationError(f"{name} must be set")
    return value


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer (got {raw!r})") from exc
    if value < minimum:
        raise ConfigurationError(f"{name} must be >= {minimum}")
    return value


def _float_env(name: str, default: float, minimum: float | None = None) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number (got {raw!r})") from exc
    if minimum is not None and value < minimum:
        raise ConfigurationError(f"{name} must be >= {minimum}")
    return value


try:
    import redis.asyncio as redis  # type: ignore
    from redis.exceptions import ResponseError  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    redis = None
    ResponseError = Exception

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

pipeline = create_pipeline()

ORCHESTRATOR_BASE_URL = os.getenv("ORCHESTRATOR_BASE_URL")
READY_STREAM = os.getenv("READY_STREAM", "jobs.ready")
DEAD_STREAM = os.getenv("DEAD_STREAM", "jobs.dead")
STATUS_ENDPOINT = os.getenv("STATUS_ENDPOINT", "/jobs/status")

REDIS_URL = _require_env("REDIS_URL")
QUEUE_GROUP = os.getenv("JOB_QUEUE_CONSUMER_GROUP", "jobs-workers")
QUEUE_CONSUMER_NAME = os.getenv("JOB_QUEUE_CONSUMER_NAME") or f"{socket.gethostname()}-{os.getpid()}"
ACK_TIMEOUT_MS = _int_env("JOB_QUEUE_ACK_TIMEOUT_MS", 60000, minimum=1000)
MAX_RETRIES = _int_env("JOB_QUEUE_MAX_RETRIES", 3, minimum=1)
BACKOFF_BASE_SECONDS = _float_env("JOB_QUEUE_BACKOFF_BASE_SECONDS", 5.0, minimum=0.1)
BACKOFF_MULTIPLIER = _float_env("JOB_QUEUE_BACKOFF_MULTIPLIER", 2.0, minimum=1.0)
BACKOFF_MAX_SECONDS = _float_env("JOB_QUEUE_BACKOFF_MAX_SECONDS", 60.0, minimum=BACKOFF_BASE_SECONDS)
CLAIM_BATCH_SIZE = _int_env("JOB_QUEUE_CLAIM_BATCH_SIZE", 10, minimum=1)
READ_COUNT = _int_env("JOB_QUEUE_READ_COUNT", 5, minimum=1)
BLOCK_MS = _int_env("JOB_QUEUE_BLOCK_MS", 5000, minimum=100)


QUEUE_GROUP = os.getenv("JOB_QUEUE_CONSUMER_GROUP", "jobs-workers")
QUEUE_CONSUMER_NAME = os.getenv("JOB_QUEUE_CONSUMER_NAME") or f"{socket.gethostname()}-{os.getpid()}"
ACK_TIMEOUT_MS = int(os.getenv("JOB_QUEUE_ACK_TIMEOUT_MS", "60000"))
MAX_RETRIES = int(os.getenv("JOB_QUEUE_MAX_RETRIES", "3"))
BACKOFF_BASE_SECONDS = float(os.getenv("JOB_QUEUE_BACKOFF_BASE_SECONDS", "5"))
BACKOFF_MULTIPLIER = float(os.getenv("JOB_QUEUE_BACKOFF_MULTIPLIER", "2"))
BACKOFF_MAX_SECONDS = float(os.getenv("JOB_QUEUE_BACKOFF_MAX_SECONDS", "60"))
CLAIM_BATCH_SIZE = int(os.getenv("JOB_QUEUE_CLAIM_BATCH_SIZE", "10"))
READ_COUNT = int(os.getenv("JOB_QUEUE_READ_COUNT", "5"))
BLOCK_MS = int(os.getenv("JOB_QUEUE_BLOCK_MS", "5000"))

PAYLOAD_FIELD = "payload"
ATTEMPT_FIELD = "attempts"



@dataclass
class QueueMessage:
    message_id: str
    payload: Dict[str, object]
    attempts: int


class QueueConsumer:
    async def consume(self, stream: str) -> AsyncIterator[QueueMessage]:  # pragma: no cover - interface
        raise NotImplementedError

    async def ack(self, message: QueueMessage) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def requeue(self, message: QueueMessage, next_attempt: int, delay: float) -> None:  # pragma: no cover
        raise NotImplementedError

    async def dead_letter(self, message: QueueMessage, detail: Optional[str] = None) -> None:  # pragma: no cover
        raise NotImplementedError


class RedisStreamQueueConsumer(QueueConsumer):
    def __init__(
        self,
        redis_url: str,
        stream: str,
        group: str,
        consumer: str,
        ack_timeout_ms: int,
        dead_stream: str,
        claim_batch: int,
        read_count: int,
        block_ms: int,
    ) -> None:
        if not redis:
            raise RuntimeError("redis.asyncio is not available; install redis>=5.0")
        self._client = redis.from_url(redis_url, decode_responses=True)
        self._stream = stream
        self._group = group
        self._consumer = consumer
        self._ack_timeout_ms = ack_timeout_ms
        self._dead_stream = dead_stream
        self._claim_batch = max(1, claim_batch)
        self._read_count = max(1, read_count)
        self._block_ms = max(100, block_ms)
        self._pending_tasks: set[asyncio.Task[None]] = set()

    async def _ensure_group(self) -> None:
        try:
            await self._client.xgroup_create(self._stream, self._group, id="0", mkstream=True)
            logger.info("Created consumer group %s for stream %s", self._group, self._stream)
        except ResponseError as exc:  # pragma: no cover - already exists
            if "BUSYGROUP" not in str(exc):
                raise

    def _schedule(self, coro: Awaitable[None]) -> None:
        task = asyncio.create_task(coro)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    def _to_message(self, entry_id: str, fields: Dict[str, str]) -> QueueMessage:
        payload_raw = fields.get(PAYLOAD_FIELD, "{}")
        attempts_raw = fields.get(ATTEMPT_FIELD, "0")
        try:
            payload: Dict[str, object] = json.loads(payload_raw)
        except json.JSONDecodeError:
            payload = {}
        try:
            attempts = int(attempts_raw)
        except (TypeError, ValueError):
            attempts = 0
        return QueueMessage(message_id=entry_id, payload=payload, attempts=attempts)

    async def _iter_stale_messages(self) -> AsyncIterator[QueueMessage]:
        if self._ack_timeout_ms <= 0:
            return
        start_id = "0-0"
        while True:
            result = await self._client.xautoclaim(
                self._stream,
                self._group,
                self._consumer,
                min_idle_time=self._ack_timeout_ms,
                start_id=start_id,
                count=self._claim_batch,
            )
            if isinstance(result, (list, tuple)):
                next_start = result[0]
                entries = result[1] if len(result) > 1 else []
            else:
                next_start = result
                entries = []
            if not entries:
                if isinstance(next_start, str):
                    start_id = next_start
                break
            for entry_id, fields in entries:
                yield self._to_message(entry_id, fields)
            if isinstance(next_start, str):
                start_id = next_start

    async def consume(self, stream: str) -> AsyncIterator[QueueMessage]:
        if stream != self._stream:
            raise ValueError(f"Unexpected stream {stream}; expected {self._stream}")
        await self._ensure_group()
        while True:
            async for stale in self._iter_stale_messages():
                yield stale
            response = await self._client.xreadgroup(
                self._group,
                self._consumer,
                {self._stream: ">"},
                count=self._read_count,
                block=self._block_ms,
            )
            if not response:
                continue
            for _, entries in response:
                for entry_id, fields in entries:
                    yield self._to_message(entry_id, fields)

    async def ack(self, message: QueueMessage) -> None:
        await self._client.xack(self._stream, self._group, message.message_id)
        await self._client.xdel(self._stream, message.message_id)
        logger.debug("Acked job %s (message %s)", message.payload.get("job_id"), message.message_id)

    async def requeue(self, message: QueueMessage, next_attempt: int, delay: float) -> None:
        await self._client.xack(self._stream, self._group, message.message_id)
        await self._client.xdel(self._stream, message.message_id)

        async def _enqueue() -> None:
            if delay > 0:
                await asyncio.sleep(delay)
            await self._client.xadd(
                self._stream,
                {
                    PAYLOAD_FIELD: json.dumps(message.payload),
                    ATTEMPT_FIELD: str(next_attempt),
                },
            )

        self._schedule(_enqueue())
        logger.warning(
            "Retrying job %s (message %s) in %.1fs (attempt %s)",
            message.payload.get("job_id"),
            message.message_id,
            delay,
            next_attempt,
        )

    async def dead_letter(self, message: QueueMessage, detail: Optional[str] = None) -> None:
        await self._client.xack(self._stream, self._group, message.message_id)
        await self._client.xdel(self._stream, message.message_id)
        entry = {
            PAYLOAD_FIELD: json.dumps(message.payload),
            ATTEMPT_FIELD: str(message.attempts),
        }
        if detail:
            entry["detail"] = detail
        await self._client.xadd(self._dead_stream, entry)
        logger.error("Moved job %s (message %s) to dead-letter: %s", message.payload.get("job_id"), message.message_id, detail)


class InMemoryQueueConsumer(QueueConsumer):  # pragma: no cover - fallback for tests
    def __init__(self) -> None:
        self._queue: asyncio.Queue[QueueMessage] = asyncio.Queue()
        self._dead: list[QueueMessage] = []

    async def consume(self, stream: str) -> AsyncIterator[QueueMessage]:
        while True:
            message = await self._queue.get()
            yield message

    async def ack(self, message: QueueMessage) -> None:
        return

    async def requeue(self, message: QueueMessage, next_attempt: int, delay: float) -> None:
        async def _enqueue() -> None:
            if delay > 0:
                await asyncio.sleep(delay)
            clone = QueueMessage(
                message_id=f"{message.message_id}-retry{next_attempt}",
                payload=dict(message.payload),
                attempts=next_attempt,
            )
            await self._queue.put(clone)

        asyncio.create_task(_enqueue())

    async def dead_letter(self, message: QueueMessage, detail: Optional[str] = None) -> None:
        self._dead.append(message)


if not redis:
    raise ConfigurationError('redis.asyncio is not available; install redis>=5.0')

queue_consumer: QueueConsumer = RedisStreamQueueConsumer(
    redis_url=REDIS_URL,
    stream=READY_STREAM,
    group=QUEUE_GROUP,
    consumer=QUEUE_CONSUMER_NAME,
    ack_timeout_ms=ACK_TIMEOUT_MS,
    dead_stream=DEAD_STREAM,
    claim_batch=CLAIM_BATCH_SIZE,
    read_count=READ_COUNT,
    block_ms=BLOCK_MS,
)


class StatusReporter:
    def __init__(self, base_url: Optional[str]) -> None:
        self._base_url = base_url
        self._client: Optional[httpx.Client] = None
        if base_url:
            self._client = httpx.Client(base_url=base_url, timeout=30)

    def update(
        self,
        job_id: str,
        status: JobStatus,
        detail: Optional[str] = None,
        artefacts: Optional[Dict[str, str]] = None,
    ) -> None:
        if self._client:
            payload = {
                "job_id": job_id,
                "status": status.value,
                "detail": detail,
                "artefacts": artefacts or {},
            }
            response = self._client.post(STATUS_ENDPOINT, json=payload)
            response.raise_for_status()
        else:  # pragma: no cover - fallback
            print(f"Status update for {job_id}: {status.value} ({detail})")


def _status_detail(status: JobStatus, attempt: int) -> Optional[str]:
    base = STATUS_SUMMARY.get(status)
    if not base:
        return None
    if attempt > 1 and status not in {JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.CANCELLED}:
        return f"Attempt {attempt}: {base}"
    return base


reporter = StatusReporter(ORCHESTRATOR_BASE_URL)


def _calculate_backoff(attempt: int) -> float:
    delay = BACKOFF_BASE_SECONDS * (BACKOFF_MULTIPLIER ** max(0, attempt - 1))
    return min(delay, BACKOFF_MAX_SECONDS)


async def handle_job(message: QueueMessage) -> None:
    payload = message.payload
    job_id = str(payload.get("job_id")) if payload.get("job_id") else "unknown"
    source_type = str(payload.get("source_type")) if payload.get("source_type") else "raw_text"
    source_uri = payload.get("source_uri")

    if not source_uri:
        reporter.update(job_id, JobStatus.FAILED, detail="Missing source_uri")
        await queue_consumer.dead_letter(message, detail="Missing source_uri")
        return

    mime_type = {
        "pdf": "application/pdf",
        "image": "image/png",
    }.get(source_type, "application/octet-stream")

    attempt_number = message.attempts + 1
    reporter.update(job_id, JobStatus.PROCESSING, detail=_status_detail(JobStatus.PROCESSING, attempt_number))

    def status_callback(status: JobStatus) -> None:
        reporter.update(job_id, status, detail=_status_detail(status, attempt_number))

    def run_pipeline() -> Dict[str, object]:
        result = pipeline.run(
            task_id=job_id,
            file_path=str(source_uri),
            file_type=mime_type,
            status_callback=status_callback,
        )
        return {
            "translated_text": result.translated_text,
            "original_images": result.original_images,
        }

    try:
        output = await asyncio.to_thread(run_pipeline)
        artefacts: Dict[str, str] = {
            "translated_text": output.get("translated_text", ""),
            "original_images": json.dumps(output.get("original_images", [])),
        }
        reporter.update(
            job_id,
            JobStatus.COMPLETE,
            detail=_status_detail(JobStatus.COMPLETE, attempt_number),
            artefacts=artefacts,
        )
        await queue_consumer.ack(message)
    except Exception as exc:  # pragma: no cover - pipeline failure
        next_attempt = message.attempts + 1
        error_detail = str(exc)
        if next_attempt > MAX_RETRIES:
            reporter.update(job_id, JobStatus.FAILED, detail=error_detail)
            await queue_consumer.dead_letter(message, detail=error_detail)
            return

        delay = _calculate_backoff(next_attempt)
        reporter.update(
            job_id,
            JobStatus.PROCESSING,
            detail=f"Retrying (attempt {next_attempt}/{MAX_RETRIES}) in {delay:.1f}s: {error_detail}",
        )
        await queue_consumer.requeue(message, next_attempt, delay)


async def worker_loop() -> None:
    async for message in queue_consumer.consume(READY_STREAM):
        await handle_job(message)


def run() -> None:
    asyncio.run(worker_loop())


if __name__ == "__main__":
    run()
