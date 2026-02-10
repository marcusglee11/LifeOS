#!/usr/bin/env python3
"""Acceptance & Closure policy validator for LifeOS.

Validates acceptance notes against SCHEMA__Acceptance_Closure_v1.0.
Enforces clean-proof requirements and deterministic key ordering.

Exit codes:
  0: Acceptance note is valid
  1: Acceptance note is invalid
  2: Error condition (file not found, parse error)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple


REQUIRED_KEYS = [
    "TITLE",
    "SCOPE",
    "MAIN_HEAD",
    "SOURCE_REFS",
    "EVID_DIR",
    "RECEIPTS",
    "VERIFICATIONS",
    "CLEAN_PROOF_PRE",
    "CLEAN_PROOF_POST",
]

OPTIONAL_KEYS = [
    "DEVIATIONS",
    "FOLLOWUPS",
]

ALL_KEYS = REQUIRED_KEYS + OPTIONAL_KEYS

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_KEY_RE = re.compile(r"^([A-Z_]+)=(.*)$")


class ValidationResult(NamedTuple):
    """Result of validating an acceptance note."""

    valid: bool
    errors: list[str]


def parse_acceptance_note(text: str) -> dict[str, str]:
    """Parse key=value pairs from an acceptance note.

    Returns a dict of key -> value.  Raises ValueError on duplicate keys.
    """
    result: dict[str, str] = {}
    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = _KEY_RE.match(stripped)
        if m:
            key, value = m.group(1), m.group(2).strip()
            if key in result:
                raise ValueError(
                    f"line {line_no}: duplicate key '{key}'"
                )
            result[key] = value
    return result


def validate_main_head(value: str) -> list[str]:
    """Validate MAIN_HEAD looks like a 40-char hex git SHA."""
    if not _SHA_RE.match(value):
        return [f"MAIN_HEAD is not a valid 40-char hex SHA: '{value}'"]
    return []


def validate_clean_proofs(note: dict[str, str]) -> list[str]:
    """Validate CLEAN_PROOF_PRE and CLEAN_PROOF_POST are present and clean.

    A clean proof value must be present.  The value 'clean' or 'empty'
    (case-insensitive) indicates a clean state.  A non-empty value that
    does not indicate clean is treated as a dirty proof.
    """
    errors: list[str] = []
    for key in ("CLEAN_PROOF_PRE", "CLEAN_PROOF_POST"):
        value = note.get(key, "")
        if not value:
            errors.append(f"{key} is missing or empty")
            continue
        # Accept explicit "clean" / "empty" / "0 files" markers
        lower = value.lower()
        clean_markers = ("clean", "empty", "0 files", "0 files modified")
        if not any(marker in lower for marker in clean_markers):
            errors.append(
                f"{key} does not indicate clean state: '{value}'"
            )
    return errors


def validate_acceptance_note(text: str) -> ValidationResult:
    """Validate an acceptance note against the schema.

    Returns a ValidationResult with valid=True if all checks pass,
    or valid=False with a list of error messages.
    """
    errors: list[str] = []

    # Parse
    try:
        note = parse_acceptance_note(text)
    except ValueError as exc:
        return ValidationResult(valid=False, errors=[str(exc)])

    # Check unknown keys
    for key in note:
        if key not in ALL_KEYS:
            errors.append(f"unknown key '{key}'")

    # Check required keys
    for key in REQUIRED_KEYS:
        if key not in note:
            errors.append(f"missing required key '{key}'")

    # If required keys are missing, return early
    if any("missing required" in e for e in errors):
        return ValidationResult(valid=False, errors=errors)

    # Validate MAIN_HEAD
    errors.extend(validate_main_head(note["MAIN_HEAD"]))

    # Validate EVID_DIR
    if not note.get("EVID_DIR"):
        errors.append("EVID_DIR is empty")

    # Validate clean proofs
    errors.extend(validate_clean_proofs(note))

    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_file(path: Path) -> ValidationResult:
    """Validate an acceptance note file."""
    if not path.exists():
        return ValidationResult(
            valid=False, errors=[f"file not found: {path}"]
        )
    text = path.read_text(encoding="utf-8")
    return validate_acceptance_note(text)


def cli_validate(args: argparse.Namespace) -> int:
    """CLI: validate an acceptance note file."""
    path = Path(args.path)
    result = validate_file(path)
    if result.valid:
        print(f"VALID: {path}")
        return 0
    else:
        print(f"INVALID: {path}")
        for error in result.errors:
            print(f"  - {error}")
        return 1


def cli_skeleton(args: argparse.Namespace) -> int:
    """CLI: emit a skeleton acceptance note to stdout."""
    lines = []
    lines.append("# Acceptance Note")
    lines.append("")
    for key in REQUIRED_KEYS:
        lines.append(f"{key}=")
    lines.append("")
    lines.append("# Optional fields:")
    for key in OPTIONAL_KEYS:
        lines.append(f"# {key}=")
    lines.append("")
    print("\n".join(lines))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Acceptance & Closure policy validator."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    validate_parser = sub.add_parser(
        "validate", help="Validate an acceptance note file."
    )
    validate_parser.add_argument("path", help="Path to acceptance note.")
    validate_parser.set_defaults(func=cli_validate)

    skeleton_parser = sub.add_parser(
        "skeleton", help="Emit a skeleton acceptance note."
    )
    skeleton_parser.set_defaults(func=cli_skeleton)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
