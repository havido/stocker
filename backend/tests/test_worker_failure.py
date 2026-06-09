"""
Tests for the worker's failure path.

The full pipeline needs torch/transformers, so we don't run it here. Instead we
test the small, pure failure-handling contract: when the pipeline raises, the job
must be marked `failed` and a terminal `ERROR` sentinel (preceded by a parseable
error event) must reach the SSE channel — otherwise the frontend hangs until the
120s stream timeout.
"""

import json

from tasks import _publish_failure, FAILURE_SENTINEL, SUCCESS_SENTINEL


class FakeDB:
    def __init__(self):
        self.status = None
        self.logs = []

    def update_job_status(self, task_id, status):
        self.status = status

    def publish_log(self, task_id, msg):
        self.logs.append(msg)


def test_publish_failure_marks_job_failed():
    db = FakeDB()
    _publish_failure(db, "task-1", ValueError("scraper blew up"))
    assert db.status == "failed"


def test_publish_failure_emits_terminal_sentinel_last():
    db = FakeDB()
    _publish_failure(db, "task-1", RuntimeError("oom"))
    assert db.logs[-1] == FAILURE_SENTINEL


def test_publish_failure_emits_parseable_error_event_with_message():
    db = FakeDB()
    _publish_failure(db, "task-1", ValueError('quotes "and" newlines\n break json'))
    # The event just before the terminal must be valid JSON carrying the reason.
    event = json.loads(db.logs[-2])
    assert event["step"] == "error"
    assert "break json" in event["message"]


def test_sentinels_are_distinct():
    assert SUCCESS_SENTINEL != FAILURE_SENTINEL
