"""
Tests for src/core/approval_gate.py

Covers:
- display_preview prints correctly without errors
- prompt_user returns True on 'a'
- prompt_user returns False on 'r'
- prompt_user rejects invalid input and re-prompts
- prompt_user handles uppercase input
- prompt_user handles whitespace around input
- run returns True on approve
- run returns False on reject
- run prints approval message on approve
- run prints rejection message on reject
"""

import pytest
import os
import sys
from unittest.mock import patch
from io import StringIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.approval_gate import display_preview, prompt_user, run


# --- Helpers ---

def make_payload():
    """Create a complete payload dict for testing."""
    return {
        "date": "2026-03-22",
        "weekly_pulse": {
            "themes": [
                {"name": "Performance", "description": "Speed issues", "review_count": 15},
                {"name": "UX", "description": "Design feedback", "review_count": 10},
            ],
            "top_themes": ["Performance", "UX", "Support"],
            "quotes": [
                {"text": "The app crashes every time I try to open my portfolio and it is very frustrating", "rating": 1},
                {"text": "Love the redesigned dashboard interface, it looks clean and modern", "rating": 5},
                {"text": "Support team took 3 days to respond to my query about mutual fund exit load", "rating": 2},
            ],
            "note": "This week saw significant user feedback around performance issues and UX improvements. Several users reported app crashes on Android 14 devices.",
            "actions": [
                "Investigate crash reports on Android 14",
                "Add live chat support option",
                "Optimize dashboard load time",
            ],
        },
        "fee_scenario": "mutual fund exit load on the INDmoney platform",
        "explanation_bullets": [
            "Exit load is a fee charged on early redemption.",
            "Typically 1% if redeemed within one year.",
            "Liquid funds may have exit load for 7 days.",
            "Exit load rates are fund-specific.",
        ],
        "source_links": [
            {"label": "SEBI Regulations", "url": "https://www.sebi.gov.in/regs"},
            {"label": "AMFI Info", "url": "https://www.amfiindia.com/exit-load"},
        ],
        "last_checked": "2026-03-22",
    }


# --- display_preview tests ---

class TestDisplayPreview:
    def test_prints_without_error(self, capsys):
        """display_preview should print the preview without raising."""
        payload = make_payload()
        display_preview(payload)

        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_contains_date(self, capsys):
        """Preview should contain the date."""
        payload = make_payload()
        display_preview(payload)

        captured = capsys.readouterr()
        assert "2026-03-22" in captured.out

    def test_contains_top_themes(self, capsys):
        """Preview should list all 3 top themes."""
        payload = make_payload()
        display_preview(payload)

        captured = capsys.readouterr()
        assert "Performance" in captured.out
        assert "UX" in captured.out
        assert "Support" in captured.out

    def test_contains_fee_scenario(self, capsys):
        """Preview should show the fee scenario."""
        payload = make_payload()
        display_preview(payload)

        captured = capsys.readouterr()
        assert "exit load" in captured.out.lower()

    def test_contains_action_ideas(self, capsys):
        """Preview should list action ideas."""
        payload = make_payload()
        display_preview(payload)

        captured = capsys.readouterr()
        assert "Investigate crash reports" in captured.out
        assert "live chat" in captured.out

    def test_contains_mcp_actions(self, capsys):
        """Preview should mention pending MCP actions."""
        payload = make_payload()
        display_preview(payload)

        captured = capsys.readouterr()
        assert "Google Doc" in captured.out
        assert "Gmail draft" in captured.out

    def test_contains_quotes(self, capsys):
        """Preview should show truncated user quotes."""
        payload = make_payload()
        display_preview(payload)

        captured = capsys.readouterr()
        assert "crashes" in captured.out.lower()


# --- prompt_user tests ---

class TestPromptUser:
    @patch("builtins.input", return_value="a")
    def test_returns_true_on_approve(self, mock_input):
        """Should return True when user types 'a'."""
        assert prompt_user() is True

    @patch("builtins.input", return_value="r")
    def test_returns_false_on_reject(self, mock_input):
        """Should return False when user types 'r'."""
        assert prompt_user() is False

    @patch("builtins.input", side_effect=["x", "invalid", "a"])
    def test_rejects_invalid_then_accepts(self, mock_input, capsys):
        """Should reject invalid inputs and re-prompt until 'a' or 'r'."""
        result = prompt_user()

        assert result is True
        assert mock_input.call_count == 3

        captured = capsys.readouterr()
        assert "Invalid input" in captured.out

    @patch("builtins.input", return_value="A")
    def test_handles_uppercase(self, mock_input):
        """Should accept 'A' as approve (case-insensitive)."""
        assert prompt_user() is True

    @patch("builtins.input", return_value="R")
    def test_handles_uppercase_reject(self, mock_input):
        """Should accept 'R' as reject (case-insensitive)."""
        assert prompt_user() is False

    @patch("builtins.input", return_value="  a  ")
    def test_handles_whitespace(self, mock_input):
        """Should handle whitespace around input."""
        assert prompt_user() is True

    @patch("builtins.input", side_effect=["", " ", "r"])
    def test_rejects_empty_input(self, mock_input, capsys):
        """Empty input should be rejected."""
        result = prompt_user()

        assert result is False
        assert mock_input.call_count == 3


# --- run tests ---

class TestRun:
    @patch("builtins.input", return_value="a")
    def test_returns_true_on_approve(self, mock_input):
        """run should return True when user approves."""
        result = run(make_payload())
        assert result is True

    @patch("builtins.input", return_value="r")
    def test_returns_false_on_reject(self, mock_input):
        """run should return False when user rejects."""
        result = run(make_payload())
        assert result is False

    @patch("builtins.input", return_value="a")
    def test_prints_approved_message(self, mock_input, capsys):
        """Should print approval message."""
        run(make_payload())

        captured = capsys.readouterr()
        assert "Approved" in captured.out
        assert "Triggering MCP actions" in captured.out

    @patch("builtins.input", return_value="r")
    def test_prints_rejected_message(self, mock_input, capsys):
        """Should print rejection message."""
        run(make_payload())

        captured = capsys.readouterr()
        assert "Rejected" in captured.out
        assert "No data written" in captured.out
