"""
Tests for src/ui/app.py

Covers:
- GET / serves dashboard HTML
- GET /api/status returns correct state
- GET /api/payload returns payload or 404
- POST /api/approve triggers MCP and sets state, handles recipients
- POST /api/reject sets state
"""

import os
import sys
import pytest
import json
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.ui.app import app, app_state, start_ui


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def reset_state():
    # Reset state before each test
    app_state["payload"] = None
    app_state["status"] = "Initializing..."
    app_state["action_taken"] = False


def make_payload():
    return {
        "date": "2026-03-22",
        "weekly_pulse": {
            "themes": [], "top_themes": [], "quotes": [], "note": "Test", "actions": []
        },
        "fee_scenario": "Test fee",
        "explanation_bullets": [],
        "source_links": [],
        "last_checked": "2026-03-22"
    }


def test_index_route(client, reset_state):
    """GET / should return HTML."""
    res = client.get("/")
    assert res.status_code == 200
    assert b"<!DOCTYPE html>" in res.data
    assert b"INDmoney AI" in res.data


def test_status_route(client, reset_state):
    """GET /api/status should return current status."""
    app_state["status"] = "Ready Test"
    app_state["action_taken"] = False

    res = client.get("/api/status")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "Ready Test"
    assert data["action_taken"] is False


def test_payload_route_no_payload(client, reset_state):
    """GET /api/payload should return 404 if no payload."""
    res = client.get("/api/payload")
    assert res.status_code == 404
    assert b"No payload available" in res.data


def test_payload_route_with_payload(client, reset_state):
    """GET /api/payload should return payload if present."""
    payload = make_payload()
    app_state["payload"] = payload

    res = client.get("/api/payload")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["date"] == "2026-03-22"


@patch("src.ui.app.append_to_doc", return_value=True)
@patch("src.ui.app.create_draft", return_value=True)
def test_approve_success(m_draft, m_doc, client, reset_state):
    """POST /api/approve should trigger MCP and update status."""
    payload = make_payload()
    app_state["payload"] = payload
    app_state["action_taken"] = False

    res = client.post("/api/approve", json={"recipients": ["ui@test.com"]})
    
    assert res.status_code == 200
    m_doc.assert_called_once_with(payload)
    m_draft.assert_called_once_with(payload)
    
    assert os.getenv("DRAFT_RECIPIENT") == "ui@test.com"
    assert app_state["action_taken"] is True
    assert "Approved" in app_state["status"]


def test_approve_already_taken(client, reset_state):
    """POST /api/approve should fail if action already taken."""
    app_state["action_taken"] = True
    
    res = client.post("/api/approve", json={})
    assert res.status_code == 400
    assert b"Action already taken" in res.data


def test_reject_success(client, reset_state):
    """POST /api/reject should update status to Rejected and mark taken."""
    app_state["action_taken"] = False
    
    res = client.post("/api/reject")
    assert res.status_code == 200
    
    assert app_state["action_taken"] is True
    assert app_state["status"] == "Rejected by User"


def test_reject_already_taken(client, reset_state):
    """POST /api/reject should fail if action already taken."""
    app_state["action_taken"] = True
    
    res = client.post("/api/reject")
    assert res.status_code == 400
    assert b"Action already taken" in res.data
