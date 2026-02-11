from pathlib import Path

from runtime.tools.openclaw_memory_policy_guard import scan_workspace


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_missing_front_matter_fails(tmp_path: Path):
    _write(tmp_path / "MEMORY.md", "# Memory\n")
    _write(tmp_path / "memory" / "daily.md", "# no front matter\n")
    summary = scan_workspace(tmp_path)
    assert summary["policy_ok"] is False
    assert any(v["rule"] == "MISSING_FRONT_MATTER" for v in summary["violations"])


def test_secret_classification_fails(tmp_path: Path):
    _write(tmp_path / "MEMORY.md", "# Memory\n")
    _write(
        tmp_path / "memory" / "entry.md",
        "---\nclassification: SECRET\nretention: 30d\n---\nbody\n",
    )
    summary = scan_workspace(tmp_path)
    assert summary["policy_ok"] is False
    assert any(v["rule"] == "CLASSIFICATION_SECRET_DISALLOWED" for v in summary["violations"])


def test_token_like_string_fails_and_is_redacted(tmp_path: Path):
    _write(tmp_path / "MEMORY.md", "# Memory\n")
    _write(
        tmp_path / "memory" / "entry.md",
        "---\nclassification: INTERNAL\nretention: 180d\n---\napiKey: sk-abcdefghijklmnop\n",
    )
    summary = scan_workspace(tmp_path)
    assert summary["policy_ok"] is False
    token_violations = [v for v in summary["violations"] if v["rule"] == "SECRET_PATTERN_BLOCKED"]
    assert token_violations
    assert "abcdefghijklmnop" not in token_violations[0]["snippet"]
    assert "[REDACTED]" in token_violations[0]["snippet"]


def test_valid_entry_passes(tmp_path: Path):
    _write(tmp_path / "MEMORY.md", "# OpenClaw Memory\nNo secrets.\n")
    _write(
        tmp_path / "memory" / "daily" / "2026-02-11.md",
        "---\n"
        "title: Daily note\n"
        "classification: INTERNAL\n"
        "retention: 180d\n"
        "created_utc: 2026-02-11T00:00:00Z\n"
        "sources:\n"
        "  - seeded by test\n"
        "---\n"
        "seed phrase lobster-memory-seed-001\n",
    )
    summary = scan_workspace(tmp_path)
    assert summary["policy_ok"] is True
    assert summary["violations_count"] == 0
