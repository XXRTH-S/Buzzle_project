"""ความคืบหน้าของงาน — worker publish, API stream ต่อให้เบราว์เซอร์ผ่าน SSE"""
import json

import redis

from .config import settings

_client: redis.Redis | None = None


def client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings().redis_url, decode_responses=True)
    return _client


def channel(media_id: str) -> str:
    return f"progress:{media_id}"


def publish(media_id: str, step: str, state: str,
            progress: float | None = None, **extra) -> None:
    payload = {"step": step, "state": state, "progress": progress, **extra}
    try:
        client().publish(channel(media_id), json.dumps(payload, ensure_ascii=False))
    except redis.RedisError:
        # Progress is best effort; persisted stage results remain authoritative.
        pass


def subscribe(media_id: str):
    pubsub = client().pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(channel(media_id))
    return pubsub
