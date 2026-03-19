from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.campaign.gate5_soak_runner import apply_reset
from scripts.campaign.gate5_soak_validator import validate_soak_result


def test_hard_reset_resets_counter() -> None:
    assert apply_reset(8, "governance_escape") == 0


def test_soft_reset_subtracts_one() -> None:
    assert apply_reset(8, "parse_failure") == 7


def test_clean_increments_counter() -> None:
    assert apply_reset(8, "clean") == 9


def test_unknown_reason_raises() -> None:
    with pytest.raises(ValueError, match="unrecognized reason"):
        apply_reset(8, "cleen")


def test_soak_pass_16_clean(tmp_path: Path) -> None:
    result = {
        "clean_run_count": 16,
        "session_count": 4,
        "calendar_days": 2,
        "distribution": {
            "propose": 6,
            "clear_direct": 4,
            "ambiguous_or_protected": 2,
            "repeated_pairs": 2,
            "continuity": 2,
        },
    }
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    assert validate_soak_result(path)["pass"] is True


def test_soak_fail_15_clean(tmp_path: Path) -> None:
    result = {
        "clean_run_count": 15,
        "session_count": 4,
        "calendar_days": 2,
        "distribution": {
            "propose": 6,
            "clear_direct": 4,
            "ambiguous_or_protected": 2,
            "repeated_pairs": 2,
            "continuity": 2,
        },
    }
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    assert validate_soak_result(path)["pass"] is False


def test_distribution_check(tmp_path: Path) -> None:
    result = {
        "clean_run_count": 16,
        "session_count": 4,
        "calendar_days": 2,
        "distribution": {
            "propose": 5,
            "clear_direct": 4,
            "ambiguous_or_protected": 2,
            "repeated_pairs": 2,
            "continuity": 2,
        },
    }
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    assert "propose_distribution_below_threshold" in validate_soak_result(path)["violations"]
