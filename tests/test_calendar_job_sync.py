import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from actions.calendar_job_sync import format_daily_digest_body, sync_daily_digest_events


def test_format_daily_digest_body_single_role():
    jobs = [
        {
            "job_key": "stripe_ml_engineer",
            "company": "Stripe",
            "title": "Machine Learning Engineer",
            "timestamp": 1795006800,
            "apply_url": "https://stripe.com/jobs/123",
            "resume_pdf": "output/Stripe_Resume.pdf",
        }
    ]
    body = format_daily_digest_body("2026-11-18", jobs)
    assert body["start"]["date"] == "2026-11-18"
    assert body["end"]["date"] == "2026-11-19"
    assert body["summary"] == "📝 Applied: Stripe - Machine Learning Engineer"
    assert "Stripe — Machine Learning Engineer" in body["description"]
    assert "https://stripe.com/jobs/123" in body["description"]
    assert body["extendedProperties"]["private"]["date"] == "2026-11-18"
    assert body["extendedProperties"]["private"]["count"] == "1"


def test_format_daily_digest_body_multiple_roles():
    jobs = [
        {"job_key": "anduril_mle", "company": "Anduril", "title": "ML Engineer", "timestamp": 1795006620},
        {"job_key": "basis_researcher", "company": "Basis", "title": "Researcher", "timestamp": 1795006800},
    ]
    body = format_daily_digest_body("2026-11-18", jobs)
    assert body["start"]["date"] == "2026-11-18"
    assert body["end"]["date"] == "2026-11-19"
    assert "📝 Applied: 2 roles (Anduril, Basis)" == body["summary"]
    assert "Total Roles Applied: 2" in body["description"]


def test_sync_daily_digest_events_stale_cleanup(monkeypatch):
    mock_service = MagicMock()
    events_mock = MagicMock()
    mock_service.events.return_value = events_mock

    # Mock list() returns an existing digest for yesterday (2026-11-17)
    list_mock = MagicMock()
    list_mock.execute.return_value = {
        "items": [
            {
                "id": "stale_tuesday_event_id",
                "summary": "📝 Applied: 1 roles (Stripe)",
                "start": {"date": "2026-11-17"},
                "extendedProperties": {"private": {"source": "anubis_daily_digest", "date": "2026-11-17"}},
            }
        ]
    }
    events_mock.list.return_value = list_mock

    # Mock insert / patch / delete
    insert_mock = MagicMock()
    insert_mock.execute.return_value = {"id": "new_wednesday_event_id"}
    events_mock.insert.return_value = insert_mock

    delete_mock = MagicMock()
    delete_mock.execute.return_value = {}
    events_mock.delete.return_value = delete_mock

    # Mock history with 1 job on Wednesday 2026-11-18
    fake_history = [
        {
            "job_key": "anduril_mle",
            "company": "Anduril",
            "title": "ML Engineer",
            "status": "applied",
            "timestamp": 1795006800,  # 2026-11-18
            "iso_date": "2026-11-18T13:00:00+00:00",
        }
    ]
    monkeypatch.setattr("actions.calendar_job_sync._load_json", lambda path, default: fake_history)
    monkeypatch.setattr("actions.calendar_job_sync.get_target_calendar_id", lambda: "primary")
    monkeypatch.setattr("actions.calendar_job_sync.cleanup_legacy_individual_events", lambda s: 0)

    result = sync_daily_digest_events(service=mock_service)

    assert result["status"] == "success"
    assert result["digests_created"] == 1
    assert result["stale_digests_deleted"] == 1
    events_mock.delete.assert_called_with(calendarId="primary", eventId="stale_tuesday_event_id")
