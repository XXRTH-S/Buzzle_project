"""การเข้าถึงฐานข้อมูลด้วย SQL ตรง ๆ ไม่มี ORM — schema อยู่ใน app/schema.sql"""
from contextlib import contextmanager

from psycopg import Connection, connect
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import settings

_pool: ConnectionPool | None = None


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            settings().database_url,
            min_size=1,
            max_size=8,
            kwargs={"row_factory": dict_row},
            open=True,
        )
    return _pool


@contextmanager
def conn():
    """ยืม connection จาก pool — commit ให้อัตโนมัติถ้าไม่ raise"""
    with pool().connection() as c:
        yield c


def one(sql: str, params: tuple = ()) -> dict | None:
    with conn() as c:
        return c.execute(sql, params).fetchone()


def many(sql: str, params: tuple = ()) -> list[dict]:
    with conn() as c:
        return c.execute(sql, params).fetchall()


def run(sql: str, params: tuple = ()) -> None:
    with conn() as c:
        c.execute(sql, params)


def standalone() -> Connection:
    """connection แยกสำหรับ worker ที่รันยาว — ไม่ยืมจาก pool ของ API"""
    return connect(settings().database_url, row_factory=dict_row, autocommit=True)
