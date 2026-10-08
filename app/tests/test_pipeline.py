"""Offline regression tests. Run in Docker; no provider requests."""
import unittest
from unittest.mock import MagicMock, patch

from app.tasks import pipeline
from app.summaries.run import format_transcript


class PipelineTests(unittest.TestCase):
    def test_dispatch_after_unlock(self):
        order = []
        lock = MagicMock()
        lock.__enter__.side_effect = lambda: order.append("lock")
        lock.__exit__.side_effect = lambda *args: order.append("unlock")
        queue = MagicMock()
        queue.enqueue.side_effect = lambda *args: order.append("enqueue")

        @pipeline.serialized
        def stage(mid):
            order.append("work")
            pipeline.dispatch(queue, str, mid)

        with patch.object(pipeline, "media_lock", return_value=lock), patch.object(pipeline.db, "one", return_value={"id": "m"}):
            stage("m")
        self.assertEqual(order, ["lock", "work", "unlock", "enqueue"])

    def test_deleted_media_does_not_run(self):
        work = MagicMock()
        with patch.object(pipeline, "media_lock"), patch.object(pipeline.db, "one", return_value=None):
            pipeline.serialized(work)("deleted")
        work.assert_not_called()

    @patch.object(pipeline.db, "one", return_value={"summary_template": "key_points"})
    def test_join_preserves_rows(self, _media):
        with patch.object(pipeline, "_claim", return_value=True), patch.object(pipeline, "_status"), patch.object(pipeline, "_finish"), patch.object(pipeline.events, "publish"), patch.object(pipeline.db, "many", return_value=[{"id": 1, "start_ms": 120, "end_ms": 760}]), patch.object(pipeline.db, "run") as write, patch.object(pipeline, "dispatch"), patch.object(pipeline, "cpu"):
            pipeline.join_step.__wrapped__("m")
        write.assert_not_called()

    @patch.object(pipeline.db, "one", return_value={"summary_template": "key_points"})
    def test_join_rejects_invalid_timing(self, _media):
        with patch.object(pipeline, "_claim", return_value=True), patch.object(pipeline, "_status"), patch.object(pipeline, "_fail"), patch.object(pipeline.events, "publish"), patch.object(pipeline.db, "many", return_value=[{"id": 1, "start_ms": 900, "end_ms": 200}]):
            with self.assertRaises(ValueError):
                pipeline.join_step.__wrapped__("m")

    def test_empty_edit_does_not_restore_model_text(self):
        transcript = format_transcript([{"start_ms": 0, "speaker": None, "text_model": "ORIGINAL", "text_edited": ""}])
        self.assertNotIn("ORIGINAL", transcript)

    def test_finished_claim_is_not_reexecuted(self):
        connection = MagicMock()
        connection.execute.return_value.fetchone.return_value = None
        with patch.object(pipeline.db, "conn") as conn:
            conn.return_value.__enter__.return_value = connection
            self.assertFalse(pipeline._claim("m", "asr"))
            sql, params = connection.execute.call_args.args
            self.assertIn("jobs.state <> 'done' or %s", sql)
            self.assertEqual(params, ("m", "asr", False))


if __name__ == "__main__":
    unittest.main()
