"""
Tests for src/core/assembler.py

Covers:
- assemble output contains all required keys
- assemble correctly maps pulse fields
- assemble correctly maps fee fields
- assemble uses today's date
- save creates the file in the outputs/ directory
- save writes valid JSON
- save file contains correct data
- run returns the assembled payload
"""

import pytest
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.assembler import assemble, save, run


# --- Helpers ---

def make_pulse():
    return {
        "themes": [
            {"name": "Performance", "description": "Speed issues", "review_count": 15},
            {"name": "UX", "description": "Design feedback", "review_count": 10},
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
            "Redesign settings page",
            "Add live chat support",
        ],
    }


def make_fee():
    return {
        "scenario": "mutual fund exit load on the INDmoney platform",
        "bullets": [
            "Exit load is a fee charged on early redemption.",
            "Typically 1% if redeemed within one year for equity funds.",
            "Liquid funds may have exit load for 7 days.",
            "Exit load rates are fund-specific.",
        ],
        "source_links": [
            {"label": "SEBI Regulations", "url": "https://www.sebi.gov.in/regs"},
            {"label": "AMFI Info", "url": "https://www.amfiindia.com/exit-load"},
        ],
        "last_checked": "2026-03-22",
    }


# --- assemble tests ---

class TestAssemble:
    def test_contains_all_required_keys(self):
        """Output must have: date, weekly_pulse, fee_scenario, explanation_bullets, source_links, last_checked."""
        result = assemble(make_pulse(), make_fee())

        required_keys = {"date", "weekly_pulse", "fee_scenario", "explanation_bullets", "source_links", "last_checked"}
        assert set(result.keys()) == required_keys

    def test_weekly_pulse_contains_all_fields(self):
        """weekly_pulse must have: themes, top_themes, quotes, note, actions."""
        result = assemble(make_pulse(), make_fee())

        pulse_keys = {"themes", "top_themes", "quotes", "note", "actions"}
        assert set(result["weekly_pulse"].keys()) == pulse_keys

    def test_maps_pulse_themes(self):
        """Themes should come from the pulse dict."""
        pulse = make_pulse()
        result = assemble(pulse, make_fee())
        assert result["weekly_pulse"]["themes"] == pulse["themes"]

    def test_maps_pulse_top_themes(self):
        """Top themes should come from the pulse dict."""
        pulse = make_pulse()
        result = assemble(pulse, make_fee())
        assert result["weekly_pulse"]["top_themes"] == pulse["top_themes"]

    def test_maps_pulse_quotes(self):
        """Quotes should come from the pulse dict."""
        pulse = make_pulse()
        result = assemble(pulse, make_fee())
        assert result["weekly_pulse"]["quotes"] == pulse["quotes"]

    def test_maps_pulse_note(self):
        """Note should come from the pulse dict."""
        pulse = make_pulse()
        result = assemble(pulse, make_fee())
        assert result["weekly_pulse"]["note"] == pulse["note"]

    def test_maps_pulse_actions(self):
        """Actions should come from the pulse dict."""
        pulse = make_pulse()
        result = assemble(pulse, make_fee())
        assert result["weekly_pulse"]["actions"] == pulse["actions"]

    def test_maps_fee_scenario(self):
        """fee_scenario should come from the fee dict."""
        fee = make_fee()
        result = assemble(make_pulse(), fee)
        assert result["fee_scenario"] == fee["scenario"]

    def test_maps_fee_bullets(self):
        """explanation_bullets should come from the fee dict."""
        fee = make_fee()
        result = assemble(make_pulse(), fee)
        assert result["explanation_bullets"] == fee["bullets"]

    def test_maps_fee_source_links(self):
        """source_links should come from the fee dict."""
        fee = make_fee()
        result = assemble(make_pulse(), fee)
        assert result["source_links"] == fee["source_links"]

    def test_maps_fee_last_checked(self):
        """last_checked should come from the fee dict."""
        fee = make_fee()
        result = assemble(make_pulse(), fee)
        assert result["last_checked"] == fee["last_checked"]

    def test_date_is_today(self):
        """date should be today's date in ISO format."""
        result = assemble(make_pulse(), make_fee())
        assert result["date"] == date.today().isoformat()


# --- save tests ---

class TestSave:
    def test_creates_file(self, tmp_path, monkeypatch):
        """save should create a JSON file in the outputs directory."""
        monkeypatch.chdir(tmp_path)

        payload = assemble(make_pulse(), make_fee())
        path = save(payload)

        assert os.path.exists(path)
        assert path.endswith(".json")

    def test_file_contains_valid_json(self, tmp_path, monkeypatch):
        """Saved file should contain valid JSON."""
        monkeypatch.chdir(tmp_path)

        payload = assemble(make_pulse(), make_fee())
        path = save(payload)

        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert isinstance(loaded, dict)

    def test_file_contains_correct_data(self, tmp_path, monkeypatch):
        """Saved file should contain the exact payload."""
        monkeypatch.chdir(tmp_path)

        payload = assemble(make_pulse(), make_fee())
        path = save(payload)

        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["date"] == payload["date"]
        assert loaded["fee_scenario"] == payload["fee_scenario"]
        assert loaded["weekly_pulse"]["note"] == payload["weekly_pulse"]["note"]

    def test_creates_outputs_directory(self, tmp_path, monkeypatch):
        """save should create the outputs/ directory if it doesn't exist."""
        monkeypatch.chdir(tmp_path)

        payload = assemble(make_pulse(), make_fee())
        save(payload)

        assert os.path.isdir(os.path.join(tmp_path, "outputs"))

    def test_filename_contains_date(self, tmp_path, monkeypatch):
        """Filename should contain today's date."""
        monkeypatch.chdir(tmp_path)

        payload = assemble(make_pulse(), make_fee())
        path = save(payload)

        assert date.today().isoformat() in os.path.basename(path)


# --- run tests ---

class TestRun:
    def test_returns_payload_dict(self, tmp_path, monkeypatch):
        """run should return the assembled payload dict."""
        monkeypatch.chdir(tmp_path)

        result = run(make_pulse(), make_fee())

        assert isinstance(result, dict)
        assert "date" in result
        assert "weekly_pulse" in result
        assert "fee_scenario" in result

    def test_creates_file(self, tmp_path, monkeypatch):
        """run should create the output file."""
        monkeypatch.chdir(tmp_path)

        run(make_pulse(), make_fee())

        output_files = os.listdir(os.path.join(tmp_path, "outputs"))
        assert len(output_files) == 1
        assert output_files[0].endswith(".json")
