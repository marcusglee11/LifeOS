from pathlib import Path

from runtime.tools.council_v2_dogfood_review import (
    _build_review_packet_markdown,
    _parse_dotenv,
    _terminal_outcome,
)


def test_parse_dotenv_supports_export_comments_and_quotes() -> None:
    env = _parse_dotenv(
        """
        # comment
        export ZEN_REVIEWER_KEY="abc123"
        SIMPLE=value
        SINGLE='quoted'
        BROKEN_LINE
        """
    )
    assert env["ZEN_REVIEWER_KEY"] == "abc123"
    assert env["SIMPLE"] == "value"
    assert env["SINGLE"] == "quoted"
    assert "BROKEN_LINE" not in env


def test_terminal_outcome_fail_closed() -> None:
    assert _terminal_outcome(mock_ok=True, live_ok=True, packet_ok=True) == "PASS"
    assert _terminal_outcome(mock_ok=False, live_ok=True, packet_ok=True) == "BLOCKED"
    assert _terminal_outcome(mock_ok=True, live_ok=False, packet_ok=True) == "BLOCKED"
    assert _terminal_outcome(mock_ok=True, live_ok=True, packet_ok=False) == "BLOCKED"


def test_review_packet_has_required_validator_sections(tmp_path: Path) -> None:
    mock_log = tmp_path / "mock.log"
    live_log = tmp_path / "live.log"
    live_result = tmp_path / "live_result.json"
    summary_json = tmp_path / "summary.json"

    mock_log.write_text("mock", encoding="utf-8")
    live_log.write_text("live", encoding="utf-8")
    live_result.write_text('{"status":"complete"}', encoding="utf-8")
    summary_json.write_text('{"ok":true}', encoding="utf-8")

    text = _build_review_packet_markdown(
        terminal_outcome="PASS",
        mock_log=Path("artifacts/council_reviews/mock.log"),
        live_log=Path("artifacts/council_reviews/live.log"),
        live_result=Path("artifacts/council_reviews/live_result.json"),
        summary_json=Path("artifacts/council_reviews/summary.json"),
    )

    required_sections = [
        "# Scope Envelope",
        "# Summary",
        "# Issue Catalogue",
        "# Acceptance Criteria",
        "# Closure Evidence Checklist",
        "# Non-Goals",
        "# Appendix",
    ]
    for marker in required_sections:
        assert marker in text

    assert "| ID | Criterion | Status | Evidence Pointer | SHA-256 |" in text
