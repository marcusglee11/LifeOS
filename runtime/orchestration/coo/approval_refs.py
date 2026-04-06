"""Shared approval-ref validation helpers for governance rulings."""

from __future__ import annotations

import re
from pathlib import Path

_GOVERNANCE_ROOT = Path("docs") / "01_governance"
_DECISION_MARKER_RE = re.compile(r"^\*\*Decision\*\*: (RATIFIED|APPROVED)$", re.MULTILINE)


def approval_ref_error(approval_ref: str, repo_root: Path) -> str | None:
    """Return an error string when approval_ref is invalid, else None."""
    ruling_path = (repo_root / approval_ref).resolve()
    gov_root = (repo_root / _GOVERNANCE_ROOT).resolve()
    if not ruling_path.is_relative_to(gov_root):
        return f"approval_ref {approval_ref!r} is outside docs/01_governance/"
    if not ruling_path.is_file():
        return f"approval_ref {approval_ref!r} does not exist"
    text = ruling_path.read_text(encoding="utf-8")
    if not _DECISION_MARKER_RE.search(text):
        return (
            f"approval_ref {approval_ref!r} does not contain a structured approval marker "
            "(**Decision**: RATIFIED or **Decision**: APPROVED)"
        )
    return None
