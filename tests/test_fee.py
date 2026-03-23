"""
Tests for src/fee/fee_explainer.py

Covers:
- build_prompt returns a non-empty string containing the fee scenario
- parse_response strips markdown fences before parsing
- parse_response raises ValueError on invalid JSON
- validate raises if bullets < 4
- validate raises if bullets > 6
- validate allows 4-6 bullets
- validate replaces sources with fallback if domain not approved
- validate replaces sources with fallback if count != 2
- validate keeps sources if domains are approved
- validate adds last_checked field
- validate last_checked is today's date
"""

import pytest
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.fee.fee_explainer import (
    build_prompt,
    parse_response,
    validate,
    FALLBACK_SOURCES,
    APPROVED_SOURCE_DOMAINS,
    FEE_SCENARIO,
)


# --- Helpers ---

def make_valid_output(**overrides):
    """Create a valid fee explainer output dict for testing."""
    base = {
        "scenario": "mutual fund exit load on the INDmoney platform",
        "bullets": [
            "Exit load is a fee charged when investors redeem mutual fund units before a specified period.",
            "The standard exit load for equity mutual funds is typically 1% if redeemed within one year.",
            "Liquid funds generally do not carry an exit load after 7 days of investment.",
            "Exit load rates and holding periods are defined by each fund house in the scheme document.",
        ],
        "source_links": [
            {
                "label": "SEBI Mutual Fund Regulations",
                "url": "https://www.sebi.gov.in/legal/regulations/mutual-fund-regulations.html"
            },
            {
                "label": "AMFI Exit Load Info",
                "url": "https://www.amfiindia.com/investor-corner/knowledge-center/exit-load.html"
            }
        ],
    }
    base.update(overrides)
    return base


# --- build_prompt tests ---

class TestBuildPrompt:
    def test_returns_non_empty_string(self):
        """Prompt should be a non-empty string."""
        prompt = build_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_contains_fee_scenario(self):
        """Prompt should contain the fee scenario text."""
        prompt = build_prompt()
        assert FEE_SCENARIO in prompt

    def test_contains_json_schema(self):
        """Prompt should include the expected JSON schema fields."""
        prompt = build_prompt()
        assert '"scenario"' in prompt
        assert '"bullets"' in prompt
        assert '"source_links"' in prompt

    def test_contains_rules(self):
        """Prompt should contain key rules."""
        prompt = build_prompt()
        assert "neutral" in prompt.lower()
        assert "factual" in prompt.lower()
        assert "forbidden words" in prompt.lower()


# --- parse_response tests ---

class TestParseResponse:
    def test_parses_clean_json(self):
        """Should parse valid JSON without fences."""
        raw = json.dumps(make_valid_output())
        result = parse_response(raw)
        assert result["scenario"] == FEE_SCENARIO

    def test_strips_json_fence(self):
        """Should strip ```json ... ``` fences."""
        inner = json.dumps(make_valid_output())
        raw = f"```json\n{inner}\n```"
        result = parse_response(raw)
        assert "bullets" in result

    def test_strips_plain_fence(self):
        """Should strip ``` ... ``` fences."""
        inner = json.dumps(make_valid_output())
        raw = f"```\n{inner}\n```"
        result = parse_response(raw)
        assert "bullets" in result

    def test_raises_on_invalid_json(self):
        """Should raise ValueError for unparseable content."""
        with pytest.raises(ValueError, match="Failed to parse"):
            parse_response("not valid json {{{")

    def test_handles_whitespace(self):
        """Should handle leading/trailing whitespace."""
        inner = json.dumps(make_valid_output())
        raw = f"\n  {inner}  \n"
        result = parse_response(raw)
        assert "bullets" in result


# --- validate tests ---

class TestValidate:
    def test_valid_output_passes(self):
        """Valid output with 4 bullets and approved sources should pass."""
        output = make_valid_output()
        result = validate(output)
        assert len(result["bullets"]) == 4
        assert "last_checked" in result

    def test_raises_if_bullets_less_than_4(self):
        """Should raise if fewer than 4 bullets."""
        output = make_valid_output(bullets=[
            "Only one bullet.",
            "And two.",
            "And three.",
        ])
        with pytest.raises(ValueError, match="Expected 4-6 bullets, got 3"):
            validate(output)

    def test_raises_if_bullets_more_than_6(self):
        """Should raise if more than 6 bullets."""
        output = make_valid_output(bullets=[
            f"Bullet {i}" for i in range(7)
        ])
        with pytest.raises(ValueError, match="Expected 4-6 bullets, got 7"):
            validate(output)

    def test_allows_4_bullets(self):
        """4 bullets should be valid."""
        output = make_valid_output(bullets=[f"Bullet {i}" for i in range(4)])
        result = validate(output)
        assert len(result["bullets"]) == 4

    def test_allows_5_bullets(self):
        """5 bullets should be valid."""
        output = make_valid_output(bullets=[f"Bullet {i}" for i in range(5)])
        result = validate(output)
        assert len(result["bullets"]) == 5

    def test_allows_6_bullets(self):
        """6 bullets should be valid."""
        output = make_valid_output(bullets=[f"Bullet {i}" for i in range(6)])
        result = validate(output)
        assert len(result["bullets"]) == 6

    def test_replaces_sources_if_domain_not_approved(self):
        """Sources with non-approved domains should be replaced with fallback."""
        output = make_valid_output(source_links=[
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Exit_load"},
            {"label": "Random Blog", "url": "https://randomfinanceblog.com/exit-load"},
        ])
        result = validate(output)
        assert result["source_links"] == FALLBACK_SOURCES

    def test_replaces_sources_if_one_domain_bad(self):
        """If even one source has a bad domain, replace ALL with fallback."""
        output = make_valid_output(source_links=[
            {"label": "SEBI", "url": "https://www.sebi.gov.in/regulations"},
            {"label": "Bad Source", "url": "https://badblog.com/exit-load"},
        ])
        result = validate(output)
        assert result["source_links"] == FALLBACK_SOURCES

    def test_keeps_sources_if_all_domains_approved(self):
        """Sources with all approved domains should be kept as-is."""
        approved_sources = [
            {"label": "SEBI", "url": "https://www.sebi.gov.in/regulations/mf.html"},
            {"label": "AMFI", "url": "https://www.amfiindia.com/exit-load-info"},
        ]
        output = make_valid_output(source_links=approved_sources)
        result = validate(output)
        assert result["source_links"] == approved_sources

    def test_keeps_indmoney_domain(self):
        """indmoney.com should be an approved domain."""
        sources = [
            {"label": "INDmoney Help", "url": "https://indmoney.com/help/exit-load"},
            {"label": "SEBI", "url": "https://www.sebi.gov.in/regulations"},
        ]
        output = make_valid_output(source_links=sources)
        result = validate(output)
        assert result["source_links"] == sources

    def test_replaces_sources_if_count_not_2(self):
        """If source count != 2, replace with fallback."""
        output = make_valid_output(source_links=[
            {"label": "Only one", "url": "https://www.sebi.gov.in/one"},
        ])
        result = validate(output)
        assert result["source_links"] == FALLBACK_SOURCES

    def test_replaces_sources_if_count_is_3(self):
        """3 sources should be replaced with fallback."""
        output = make_valid_output(source_links=[
            {"label": "S1", "url": "https://www.sebi.gov.in/1"},
            {"label": "S2", "url": "https://www.amfiindia.com/2"},
            {"label": "S3", "url": "https://indmoney.com/3"},
        ])
        result = validate(output)
        assert result["source_links"] == FALLBACK_SOURCES

    def test_adds_last_checked_field(self):
        """Validation should add last_checked with today's date."""
        output = make_valid_output()
        result = validate(output)
        assert "last_checked" in result
        assert result["last_checked"] == date.today().isoformat()

    def test_last_checked_overwrites_existing(self):
        """Even if last_checked already exists, it should be set to today."""
        output = make_valid_output()
        output["last_checked"] = "2025-01-01"
        result = validate(output)
        assert result["last_checked"] == date.today().isoformat()

    def test_replaces_sources_if_empty_list(self):
        """Empty source list should be replaced with fallback."""
        output = make_valid_output(source_links=[])
        result = validate(output)
        assert result["source_links"] == FALLBACK_SOURCES

    def test_raises_if_zero_bullets(self):
        """Zero bullets should raise."""
        output = make_valid_output(bullets=[])
        with pytest.raises(ValueError, match="Expected 4-6 bullets, got 0"):
            validate(output)
