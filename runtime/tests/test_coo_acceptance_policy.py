#!/usr/bin/env python3
"""Tests for coo_acceptance_policy — Acceptance & Closure validator."""

import textwrap

import pytest

from runtime.tools.coo_acceptance_policy import (
    parse_acceptance_note,
    validate_acceptance_note,
    validate_clean_proofs,
    validate_main_head,
    REQUIRED_KEYS,
    OPTIONAL_KEYS,
)


def _make_valid_note(**overrides: str) -> str:
    """Build a valid acceptance note, overriding specific keys."""
    defaults = {
        "TITLE": "Test Acceptance",
        "SCOPE": "unit test fixture",
        "MAIN_HEAD": "a" * 40,
        "SOURCE_REFS": "commit1,commit2",
        "EVID_DIR": "artifacts/evidence/test",
        "RECEIPTS": "receipt1.txt,receipt2.txt",
        "VERIFICATIONS": "pytest -q; rc=0",
        "CLEAN_PROOF_PRE": "clean (0 files modified)",
        "CLEAN_PROOF_POST": "clean (0 files modified)",
    }
    defaults.update(overrides)
    lines = ["# Acceptance Note", ""]
    for key, value in defaults.items():
        lines.append(f"{key}={value}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# parse_acceptance_note
# ---------------------------------------------------------------------------


class TestParseAcceptanceNote:
    def test_parses_valid_note(self):
        text = _make_valid_note()
        result = parse_acceptance_note(text)
        assert result["TITLE"] == "Test Acceptance"
        assert result["MAIN_HEAD"] == "a" * 40

    def test_skips_comments_and_blanks(self):
        text = "# comment\n\nTITLE=hello\n"
        result = parse_acceptance_note(text)
        assert result == {"TITLE": "hello"}

    def test_raises_on_duplicate_key(self):
        text = "TITLE=hello\nTITLE=world\n"
        with pytest.raises(ValueError, match="duplicate key 'TITLE'"):
            parse_acceptance_note(text)


# ---------------------------------------------------------------------------
# validate_main_head
# ---------------------------------------------------------------------------


class TestValidateMainHead:
    def test_valid_sha(self):
        assert validate_main_head("a" * 40) == []

    def test_short_sha_fails(self):
        errors = validate_main_head("abc123")
        assert len(errors) == 1
        assert "not a valid 40-char hex SHA" in errors[0]

    def test_non_hex_fails(self):
        errors = validate_main_head("g" * 40)
        assert len(errors) == 1

    def test_empty_fails(self):
        errors = validate_main_head("")
        assert len(errors) == 1


# ---------------------------------------------------------------------------
# validate_clean_proofs
# ---------------------------------------------------------------------------


class TestValidateCleanProofs:
    def test_clean_proofs_pass(self):
        note = {
            "CLEAN_PROOF_PRE": "clean (0 files modified)",
            "CLEAN_PROOF_POST": "empty",
        }
        assert validate_clean_proofs(note) == []

    def test_missing_pre_fails(self):
        note = {"CLEAN_PROOF_POST": "clean"}
        errors = validate_clean_proofs(note)
        assert any("CLEAN_PROOF_PRE" in e for e in errors)

    def test_missing_post_fails(self):
        note = {"CLEAN_PROOF_PRE": "clean"}
        errors = validate_clean_proofs(note)
        assert any("CLEAN_PROOF_POST" in e for e in errors)

    def test_dirty_pre_fails(self):
        note = {
            "CLEAN_PROOF_PRE": "M runtime/cli.py",
            "CLEAN_PROOF_POST": "clean",
        }
        errors = validate_clean_proofs(note)
        assert any("CLEAN_PROOF_PRE" in e and "does not indicate clean" in e for e in errors)

    def test_dirty_post_fails(self):
        note = {
            "CLEAN_PROOF_PRE": "clean",
            "CLEAN_PROOF_POST": "3 files modified",
        }
        errors = validate_clean_proofs(note)
        assert any("CLEAN_PROOF_POST" in e and "does not indicate clean" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_acceptance_note (full)
# ---------------------------------------------------------------------------


class TestValidateAcceptanceNote:
    def test_valid_note_passes(self):
        text = _make_valid_note()
        result = validate_acceptance_note(text)
        assert result.valid is True
        assert result.errors == []

    def test_missing_required_key_fails(self):
        # Remove TITLE line
        text = _make_valid_note()
        text = "\n".join(
            line for line in text.splitlines() if not line.startswith("TITLE=")
        )
        result = validate_acceptance_note(text)
        assert result.valid is False
        assert any("missing required key 'TITLE'" in e for e in result.errors)

    def test_missing_all_required_keys(self):
        text = "# just a comment\n"
        result = validate_acceptance_note(text)
        assert result.valid is False
        assert len(result.errors) == len(REQUIRED_KEYS)

    def test_invalid_main_head_fails(self):
        text = _make_valid_note(MAIN_HEAD="not-a-sha")
        result = validate_acceptance_note(text)
        assert result.valid is False
        assert any("MAIN_HEAD" in e for e in result.errors)

    def test_empty_evid_dir_fails(self):
        text = _make_valid_note(EVID_DIR="")
        result = validate_acceptance_note(text)
        assert result.valid is False
        assert any("EVID_DIR is empty" in e for e in result.errors)

    def test_optional_keys_may_be_absent(self):
        text = _make_valid_note()
        result = validate_acceptance_note(text)
        assert result.valid is True
        # Optional keys not present, should still pass

    def test_optional_keys_may_be_present(self):
        text = _make_valid_note() + "DEVIATIONS=none\nFOLLOWUPS=Gate 6\n"
        result = validate_acceptance_note(text)
        assert result.valid is True

    def test_duplicate_key_fails(self):
        text = _make_valid_note() + "TITLE=duplicate\n"
        result = validate_acceptance_note(text)
        assert result.valid is False
        assert any("duplicate" in e for e in result.errors)

    def test_dirty_clean_proof_fails(self):
        text = _make_valid_note(
            CLEAN_PROOF_PRE="M runtime/cli.py",
            CLEAN_PROOF_POST="clean",
        )
        result = validate_acceptance_note(text)
        assert result.valid is False
        assert any("CLEAN_PROOF_PRE" in e for e in result.errors)

    def test_missing_clean_proof_post_fails(self):
        # Remove CLEAN_PROOF_POST line
        text = _make_valid_note()
        text = "\n".join(
            line
            for line in text.splitlines()
            if not line.startswith("CLEAN_PROOF_POST=")
        )
        result = validate_acceptance_note(text)
        assert result.valid is False
        assert any("CLEAN_PROOF_POST" in e for e in result.errors)

    def test_unknown_key_reported(self):
        text = _make_valid_note() + "BOGUS_KEY=value\n"
        result = validate_acceptance_note(text)
        assert result.valid is False
        assert any("unknown key" in e for e in result.errors)
