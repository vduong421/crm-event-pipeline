import sqlite3

from app import ingest, summarize


def test_ingest_and_summarize_account_funnel():
    events = [
        {"event_id": "e1", "account_id": "a1", "event_type": "signup", "timestamp": "2026-01-01", "status": "ok"},
        {"event_id": "e2", "account_id": "a1", "event_type": "activation", "timestamp": "2026-01-02", "status": "ok"},
        {"event_id": "e3", "account_id": "a2", "event_type": "signup", "timestamp": "2026-01-03", "status": "failed"},
    ]
    db = sqlite3.connect(":memory:")

    ingest(db, events)
    summary = summarize(db)

    assert summary["total_events"] == 3
    assert summary["status_counts"] == {"ok": 2, "failed": 1}
    assert summary["accounts"][0]["next_stage"] == "purchase"
    assert summary["accounts"][1]["completion_ratio"] == 0.25
