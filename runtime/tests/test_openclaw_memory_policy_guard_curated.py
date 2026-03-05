import json
from pathlib import Path

from runtime.tools.openclaw_memory_policy_guard import scan_workspace


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_curated_mode_requires_roots_file(tmp_path: Path) -> None:
    summary = scan_workspace(tmp_path, mode="curated")
    assert summary["policy_ok"] is False
    assert any(v["rule"] == "CURATED_ROOTS_FILE_REQUIRED" for v in summary["violations"])


def test_curated_mode_blocks_pii_when_enabled(tmp_path: Path) -> None:
    curated_root = tmp_path / "memory_curated"
    _write(curated_root / "note.md", "Reach me at test@example.com\n")

    roots_file = tmp_path / "roots.json"
    roots_file.write_text(json.dumps({"roots": [str(curated_root)]}), encoding="utf-8")

    summary = scan_workspace(tmp_path, mode="curated", roots_file=str(roots_file), fail_on_pii=True)
    assert summary["policy_ok"] is False
    assert any(v["rule"] == "PII_PATTERN_BLOCKED" for v in summary["violations"])


def test_curated_mode_scans_only_allowlisted_roots(tmp_path: Path) -> None:
    curated_root = tmp_path / "memory_curated"
    disallowed_root = tmp_path / "elsewhere"
    _write(curated_root / "allowed.md", "safe content\n")
    _write(disallowed_root / "secret.md", "apiKey: sk-abcdefghijklmnop\n")

    roots_file = tmp_path / "roots.json"
    roots_file.write_text(json.dumps({"roots": [str(curated_root)]}), encoding="utf-8")

    summary = scan_workspace(tmp_path, mode="curated", roots_file=str(roots_file), fail_on_pii=True)
    assert summary["policy_ok"] is True
    scanned_files = summary["scanned_files"]
    assert scanned_files == 1
