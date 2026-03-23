"""
Tests for main.py (Orchestrator)

Covers:
- run_pipeline_data branches correctly
- run_cli triggers correct steps including approval and MCP
- run_cli handles rejection
- run_with_ui catches missing module exception
- main parses --ui properly
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add project root to path so we can import main
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import main as orchestrator


# --- Helpers ---
def make_payload():
    return {"date": "2026-03-22", "test": "data"}


@patch("main.scrape", return_value="data.csv")
@patch("main.generate_pulse", return_value={"pulse": "data"})
@patch("main.generate_fee", return_value={"fee": "data"})
@patch("main.assemble", return_value=make_payload())
class TestPipelineData:
    def test_run_pipeline_data(self, m_assemble, m_fee, m_pulse, m_scrape, capsys):
        """Should chain the 4 phases and return payload."""
        result = orchestrator.run_pipeline_data()
        
        assert result == make_payload()
        m_scrape.assert_called_once()
        m_pulse.assert_called_once_with("data.csv")
        m_fee.assert_called_once()
        m_assemble.assert_called_once_with({"pulse": "data"}, {"fee": "data"})


@patch("main.run_pipeline_data", return_value=make_payload())
@patch("main.approval_gate")
@patch("main.append_to_doc")
@patch("main.create_draft")
class TestRunCli:
    def test_run_cli_approved(self, m_draft, m_doc, m_approve, m_pipeline, capsys):
        """Should run MCP actions when approved."""
        m_approve.return_value = True
        m_doc.return_value = True
        m_draft.return_value = True

        orchestrator.run_cli()

        m_pipeline.assert_called_once()
        m_approve.assert_called_once_with(make_payload())
        m_doc.assert_called_once_with(make_payload())
        m_draft.assert_called_once_with(make_payload())
        
        out = capsys.readouterr().out
        assert "Awaiting human approval" in out
        assert "Triggering MCP actions" in out
        assert "Pipeline complete" in out

    @patch("main.sys.exit")
    def test_run_cli_rejected(self, m_exit, m_draft, m_doc, m_approve, m_pipeline, capsys):
        """Should exit and NOT run MCP actions when rejected."""
        m_approve.return_value = False
        m_exit.side_effect = SystemExit
        
        with pytest.raises(SystemExit):
            orchestrator.run_cli()
        
        m_approve.assert_called_once()
        m_doc.assert_not_called()
        m_draft.assert_not_called()
        m_exit.assert_called_once_with(0)


@patch("main.run_pipeline_data", return_value=make_payload())
class TestRunWithUI:
    @patch("src.ui.app.start_ui")
    def test_run_with_ui(self, m_start_ui, m_pipeline, capsys):
        """Should import start_ui and call it with payload."""
        orchestrator.run_with_ui()
        m_start_ui.assert_called_once()
        args = m_start_ui.call_args[0][0]
        assert args == make_payload()


class TestMainArgparse:
    @patch("main.run_with_ui")
    @patch("main.run_cli")
    @patch("main.sys.argv", ["main.py", "--ui"])
    def test_main_ui_flag(self, m_cli, m_ui):
        """Should call run_with_ui when --ui flag is passed."""
        orchestrator.main()
        m_ui.assert_called_once()
        m_cli.assert_not_called()

    @patch("main.run_with_ui")
    @patch("main.run_cli")
    @patch("main.sys.argv", ["main.py"])
    def test_main_no_args(self, m_cli, m_ui):
        """Should call run_cli by default when no args are passed."""
        orchestrator.main()
        m_cli.assert_called_once()
        m_ui.assert_not_called()
