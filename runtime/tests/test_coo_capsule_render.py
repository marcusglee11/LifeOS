from __future__ import annotations

from pathlib import Path

import pytest

from runtime.tools.coo_capsule_render import CapsuleRenderError, render_marker


RENDER_KEYS = [
    "HEAD",
    "EVID",
    "RESULT_PRETTY_ERR_BYTES",
    "RC",
    "DURATION_S",
    "PYTEST_SUMMARY",
]


def _write_capsule(tmp_path: Path, result_line: str = "RESULT_PRETTY_ERR_BYTES=0") -> Path:
    capsule = tmp_path / "capsule.txt"
    capsule.write_text(
        "\n".join(
            [
                "PRE_STATUS_BEGIN",
                "(empty)",
                "PRE_STATUS_END",
                "COO_E2E_MINI_CAPSULE_BEGIN",
                "HEAD=abc1234",
                "EVID=/tmp/evidence",
                "JOB_PRETTY_ERR_BYTES=0",
                result_line,
                "RC=0",
                "DURATION_S=1",
                "PYTEST_SUMMARY=(summary not found)",
                "EVID_FILES_BEGIN",
                "stdout.txt",
                "EVID_FILES_END",
                "COO_E2E_MINI_CAPSULE_END",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return capsule


def test_render_marker_includes_result_pretty_err_bytes_once(tmp_path: Path) -> None:
    capsule = _write_capsule(tmp_path, "RESULT_PRETTY_ERR_BYTES=0")
    rendered = render_marker(capsule, RENDER_KEYS)
    assert rendered.count("RESULT_PRETTY_ERR_BYTES=") == 1
    assert "RESULT_PRETTY_ERR_BYTES=0" in rendered


def test_render_marker_fails_when_result_pretty_err_bytes_missing(tmp_path: Path) -> None:
    capsule = _write_capsule(tmp_path, "IGNORED_LINE=1")
    with pytest.raises(CapsuleRenderError, match="RESULT_PRETTY_ERR_BYTES"):
        render_marker(capsule, RENDER_KEYS)


def test_render_marker_fails_when_result_pretty_err_bytes_duplicate(tmp_path: Path) -> None:
    capsule = _write_capsule(tmp_path, "RESULT_PRETTY_ERR_BYTES=0")
    with capsule.open("a", encoding="utf-8") as handle:
        handle.write("RESULT_PRETTY_ERR_BYTES=1\n")
    with pytest.raises(CapsuleRenderError, match="RESULT_PRETTY_ERR_BYTES"):
        render_marker(capsule, RENDER_KEYS)


def test_render_marker_fails_when_result_pretty_err_bytes_not_int(tmp_path: Path) -> None:
    capsule = _write_capsule(tmp_path, "RESULT_PRETTY_ERR_BYTES=notint")
    with pytest.raises(CapsuleRenderError, match="not an integer"):
        render_marker(capsule, RENDER_KEYS)
