#!/usr/bin/env python3
"""Render the OpenClaw-facing mini capsule from canonical capsule.txt."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


MINI_BEGIN = "COO_E2E_MINI_CAPSULE_BEGIN"
MINI_END = "COO_E2E_MINI_CAPSULE_END"
DEFAULT_KEYS = [
    "HEAD",
    "EVID",
    "RESULT_PRETTY_ERR_BYTES",
    "RC",
    "DURATION_S",
    "PYTEST_SUMMARY",
]


class CapsuleRenderError(ValueError):
    """Raised when capsule projection fails validation."""


def _extract_single_mini_block(lines: list[str]) -> list[str]:
    begin_indexes = [i for i, line in enumerate(lines) if line == MINI_BEGIN]
    end_indexes = [i for i, line in enumerate(lines) if line == MINI_END]
    if len(begin_indexes) != 1 or len(end_indexes) != 1:
        raise CapsuleRenderError("mini capsule markers missing or duplicated")
    begin_index = begin_indexes[0]
    end_index = end_indexes[0]
    if begin_index >= end_index:
        raise CapsuleRenderError("mini capsule markers out of order")
    return lines[begin_index + 1 : end_index]


def _single_key_value(block_lines: list[str], key: str) -> str:
    prefix = f"{key}="
    matches = [line for line in block_lines if line.startswith(prefix)]
    if len(matches) != 1:
        raise CapsuleRenderError(f"{key} missing or duplicated")
    return matches[0].split("=", 1)[1]


def _assert_single_global(lines: list[str], key: str) -> None:
    prefix = f"{key}="
    matches = [line for line in lines if line.startswith(prefix)]
    if len(matches) != 1:
        raise CapsuleRenderError(f"{key} missing or duplicated in capsule.txt")


def render_marker(capsule_path: Path, keys: list[str]) -> str:
    lines = capsule_path.read_text(encoding="utf-8").splitlines()
    mini_block = _extract_single_mini_block(lines)
    ordered_values: list[tuple[str, str]] = []

    for key in keys:
        _assert_single_global(lines, key)
        value = _single_key_value(mini_block, key)
        ordered_values.append((key, value))

    result_err_value = dict(ordered_values)["RESULT_PRETTY_ERR_BYTES"].strip()
    if not result_err_value.isdigit():
        raise CapsuleRenderError("RESULT_PRETTY_ERR_BYTES is not an integer")
    if int(result_err_value) < 0:
        raise CapsuleRenderError("RESULT_PRETTY_ERR_BYTES is negative")

    out_lines = [MINI_BEGIN]
    out_lines.extend(f"{key}={value}" for key, value in ordered_values)
    out_lines.append(MINI_END)
    return "\n".join(out_lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render deterministic COO marker block from capsule.txt."
    )
    parser.add_argument("--capsule", required=True, help="Path to capsule.txt")
    parser.add_argument(
        "--key",
        dest="keys",
        action="append",
        default=None,
        help="Ordered key to emit (repeat for multiple keys).",
    )
    args = parser.parse_args()

    keys = args.keys or list(DEFAULT_KEYS)
    if len(set(keys)) != len(keys):
        print("CAPSULE_RENDER_ERROR: duplicate requested keys", file=sys.stderr)
        return 24

    try:
        output = render_marker(Path(args.capsule), keys)
    except CapsuleRenderError as exc:
        print(f"CAPSULE_RENDER_ERROR: {exc}", file=sys.stderr)
        return 24
    except Exception:
        print("CAPSULE_RENDER_ERROR: internal failure", file=sys.stderr)
        return 24

    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
