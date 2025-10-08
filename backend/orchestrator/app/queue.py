from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator
from typing import Any, Dict

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as redis  # type: ignore
    from redis.exceptions import ResponseError  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    redis = None
    ResponseError = Exception

PAYLOAD_FIELD = "payload"
ATTEMPT_FIELD = "attempts"


class QueuePublisher:
    async def publish(self, stream: str, payload: Dict[str, Any]) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class QueueConsumer:
    async def consume(self, stream: str) -> AsyncIterator[Dict[str, Any]]:  # pragma: no cover - interface
        raise NotImplementedError


class InMemoryQueue(QueuePublisher, QueueConsumer):
    """Asyncio-queue backed implementation for development/tests."""

    def __init__(self) -> None:
        self._queues: Dict[str, asyncio.Queue[str]] = {}
        logger.warning(
            "Using in-memory queue; configure REDIS_URL for production deployments."
        )

    def _get_queue(self, stream: str) -> asyncio.Queue[str]:
        if stream not in self._queues:
            self._queues[stream] = asyncio.Queue()
        return self._queues[stream]

    async def publish(self, stream: str, payload: Dict[str, Any]) -> None:
        envelope = json.dumps({PAYLOAD_FIELD: payload, ATTEMPT_FIELD: 0})
        await self._get_queue(stream).put(envelope)
        logger.debug("Published message to %s (in-memory).", stream)

    async def consume(self, stream: str) -> AsyncIterator[Dict[str, Any]]:
        queue = self._get_queue(stream)
        while True:
            raw = await queue.get()
            try:
                envelope = json.loads(raw)
                yield {
                    PAYLOAD_FIELD: envelope.get(PAYLOAD_FIELD, {}),
                    ATTEMPT_FIELD: envelope.get(ATTEMPT_FIELD, 0),
                }
            finally:
                queue.task_done()


class RedisStreamQueue(QueuePublisher, QueueConsumer):
    """Redis stream-backed queue offering blocking reads and delivery attempts."""

    def __init__(self, redis_url: str) -> None:
        if not redis:
            raise RuntimeError("redis.asyncio is not available; install redis>=5.0")
        if not redis_url.startswith("redis://"):
            raise ValueError("REDIS_URL must start with redis://")
        self._client = redis.from_url(redis_url, decode_responses=True)
        maxlen_env = os.getenv("JOB_QUEUE_STREAM_MAX_LENGTH")
        self._approx_maxlen = int(maxlen_env) if maxlen_env else None
        logger.info("Redis stream queue initialised for %s", redis_url)

    async def publish(self, stream: str, payload: Dict[str, Any]) -> None:
        fields = {
            PAYLOAD_FIELD: json.dumps(payload),
            ATTEMPT_FIELD: "0",
        }
        try:
            if self._approx_maxlen:
                await self._client.xadd(stream, fields, maxlen=self._approx_maxlen, approximate=True)
            else:
                await self._client.xadd(stream, fields)
            logger.debug("Published message to %s (redis stream).", stream)
        except ResponseError as exc:  # pragma: no cover - redis error path
            logger.error("Failed to publish message to %s: %s", stream, exc)
            raise

    async def consume(self, stream: str) -> AsyncIterator[Dict[str, Any]]:  # pragma: no cover - orchestrator only publishes
        raise NotImplementedError("RedisStreamQueue.consume is not used in orchestrator context")


REDIS_URL = os.getenv("REDIS_URL")


def _create_queue() -> QueuePublisher:
    if REDIS_URL:
        try:
            return RedisStreamQueue(REDIS_URL)
        except Exception as exc:  # pragma: no cover - redis unavailable
            logger.error("Falling back to in-memory queue: %s", exc)
    return InMemoryQueue()


queue = _create_queue()
