import redis
from rq import Queue

from .config import settings

_conn: redis.Redis | None = None


def _redis() -> redis.Redis:
    global _conn
    if _conn is None:
        _conn = redis.from_url(settings().redis_url)
    return _conn


def cpu() -> Queue:
    """งานทั้งหมดของทางหลัก — ASR อยู่ที่ API ไม่กินเครื่อง"""
    return Queue("cpu", connection=_redis(), default_timeout=3600)


def gpu() -> Queue:
    """เฉพาะตัวเทียบ local ใน M2 — worker ตั้ง concurrency = 1 เพราะ VRAM รองรับงานเดียว"""
    return Queue("gpu", connection=_redis(), default_timeout=7200)
