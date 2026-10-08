"""Session locks survive transaction commits and release when a worker exits."""
from contextlib import contextmanager

from . import db


class MediaBusy(RuntimeError):
    pass


@contextmanager
def media_lock(media_id: str):
    with db.standalone() as connection:
        acquired = connection.execute(
            "select pg_try_advisory_lock(hashtextextended(%s, 0)) as acquired",
            (f"buzzle:{media_id}",),
        ).fetchone()["acquired"]
        if not acquired:
            raise MediaBusy("งานนี้กำลังประมวลผล กรุณารอสักครู่")
        try:
            yield
        finally:
            connection.execute("select pg_advisory_unlock(hashtextextended(%s, 0))", (f"buzzle:{media_id}",))
