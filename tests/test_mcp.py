"""
Tests for src/mcp/doc_appender.py, src/mcp/email_drafter.py and src/mcp/auth.py

Covers:
- format_entry builds correct markdown
- format_body builds correct email body
- get_google_credentials decodes base64 securely
- append_to_doc handles direct API integration success/failure
- create_draft handles direct API integration success/failure and correct payload body structure
"""

import os
import sys
import base64
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.mcp.auth import get_google_credentials
from src.mcp.doc_appender import format_entry, append_to_doc
from src.mcp.email_drafter import format_body, create_draft

# --- Helpers ---

def make_payload():
    return {
        "date": "2026-03-22",
        "weekly_pulse": {
            "themes": [
                {"name": "Performance", "description": "Speed", "review_count": 15},
            ],
            "top_themes": ["Performance", "UX", "Support"],
            "quotes": [
                {"text": "App crashes frequently", "rating": 1},
                {"text": "Love the new UI", "rating": 5},
                {"text": "Support is slow", "rating": 2},
            ],
            "note": "This week focused on performance and UX issues.",
            "actions": [
                "Fix crash on Android 14",
                "Redesign settings",
                "Add live chat"
            ],
        },
        "fee_scenario": "mutual fund exit load on the INDmoney platform",
        "explanation_bullets": [
            "Exit load is a fee charged.",
            "Typically 1% if redeemed within one year.",
        ],
        "source_links": [
            {"label": "SEBI Info", "url": "https://www.sebi.gov.in"},
        ],
        "last_checked": "2026-03-22",
    }


# --- test_auth tests ---

class TestAuth:
    @patch("src.mcp.auth.os.getenv")
    def test_get_google_credentials_missing(self, mock_getenv):
        """Should return None if GOOGLE_CREDENTIALS_BASE64 is empty."""
        mock_getenv.return_value = None
        assert get_google_credentials() is None

    @patch("src.mcp.auth.os.getenv")
    @patch("src.mcp.auth.OAuthCredentials.from_authorized_user_info")
    def test_get_google_credentials_oauth(self, m_oauth, m_getenv):
        """Should detect refresh_token and return OAuth credentials."""
        mock_creds = {"refresh_token": "foo", "client_id": "bar"}
        b64_str = base64.b64encode(json.dumps(mock_creds).encode()).decode()
        m_getenv.return_value = b64_str
        
        m_oauth.return_value = "OAUTH_CRED_OBJ"
        res = get_google_credentials()
        
        m_oauth.assert_called_once()
        assert res == "OAUTH_CRED_OBJ"

    @patch("src.mcp.auth.os.getenv")
    @patch("src.mcp.auth.ServiceAccountCredentials.from_service_account_info")
    def test_get_google_credentials_service_account(self, m_sa, m_getenv):
        """Should detect missing refresh_token and return ServiceAccount credentials."""
        mock_creds = {"type": "service_account", "project_id": "xyz"}
        b64_str = base64.b64encode(json.dumps(mock_creds).encode()).decode()
        m_getenv.return_value = b64_str
        
        m_sa.return_value = "SA_CRED_OBJ"
        res = get_google_credentials()
        
        m_sa.assert_called_once()
        assert res == "SA_CRED_OBJ"


# --- doc_appender tests ---

class TestDocAppender:
    def test_format_entry(self):
        payload = make_payload()
        markdown = format_entry(payload)
        assert "Date: 2026-03-22" in markdown
        assert "1. Fix crash on Android 14" in markdown

    @patch("src.mcp.doc_appender.build")
    @patch("src.mcp.doc_appender.get_google_credentials")
    @patch("src.mcp.doc_appender.os.getenv")
    def test_append_to_doc_success(self, mock_getenv, mock_creds, mock_build, capsys):
        """Should return True, execute batch update, and print success."""
        mock_getenv.return_value = "doc_123"
        mock_creds.return_value = "dummy_creds"
        
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        payload = make_payload()
        assert append_to_doc(payload) is True
        
        mock_service.documents().batchUpdate.assert_called_once()
        args = mock_service.documents().batchUpdate.call_args[1]
        assert args["documentId"] == "doc_123"
        assert "insertText" in args["body"]["requests"][0]
        
        assert "appended successfully" in capsys.readouterr().out

    @patch("src.mcp.doc_appender.build")
    @patch("src.mcp.doc_appender.get_google_credentials")
    @patch("src.mcp.doc_appender.os.getenv")
    def test_append_to_doc_failure(self, mock_getenv, mock_creds, mock_build, capsys):
        mock_getenv.return_value = "doc_123"
        mock_creds.return_value = "dummy_creds"
        
        mock_service = MagicMock()
        mock_service.documents().batchUpdate.side_effect = Exception("API error")
        mock_build.return_value = mock_service
        
        assert append_to_doc(make_payload()) is False
        assert "API failed" in capsys.readouterr().out


# --- email_drafter tests ---

class TestEmailDrafter:
    def test_format_body(self):
        payload = make_payload()
        body = format_body(payload)
        assert "Top themes: Performance | UX | Support" in body

    @patch("src.mcp.email_drafter.build")
    @patch("src.mcp.email_drafter.get_google_credentials")
    @patch("src.mcp.email_drafter.os.getenv")
    def test_create_draft_success_hard_constraint_8(self, mock_getenv, mock_creds, mock_build, capsys):
        """Should return True, use drafts().create() safely."""
        mock_getenv.return_value = "test@indmoney.com"
        mock_creds.return_value = "dummy_creds"
        
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        assert create_draft(make_payload()) is True
        
        # Ensures that drafts().create was used, NOT messages().send()
        mock_service.users().drafts().create.assert_called_once()
        
        args = mock_service.users().drafts().create.call_args[1]
        assert args["userId"] == "me"
        assert "raw" in args["body"]["message"]
        
        assert "draft created successfully" in capsys.readouterr().out

    @patch("src.mcp.email_drafter.build")
    @patch("src.mcp.email_drafter.get_google_credentials")
    @patch("src.mcp.email_drafter.os.getenv")
    def test_create_draft_failure(self, mock_getenv, mock_creds, mock_build, capsys):
        mock_getenv.return_value = "test@indmoney.com"
        mock_creds.return_value = "dummy"
        
        mock_service = MagicMock()
        mock_service.users().drafts().create.side_effect = Exception("API crash")
        mock_build.return_value = mock_service

        assert create_draft(make_payload()) is False
        assert "API failed" in capsys.readouterr().out
