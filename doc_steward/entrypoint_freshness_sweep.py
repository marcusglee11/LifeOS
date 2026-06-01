"""Issue-creator adapter for doc entrypoint freshness findings.

This module is intentionally inert unless called by a sweep wrapper. It converts
read-only entrypoint freshness findings into sweep_lib-compatible fingerprint,
upsert, and issue payload records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .freshness_validator import check_entrypoint_freshness

SWEEP_ID = "inventory-hygiene-sweep"
TARGET = "lifeos-doc-entrypoint"
CHECK_ID = "readme-entrypoint-freshness"
DEFAULT_REPO = "marcusglee11/lifeos-operational-bus"
DEFAULT_LABELS = ["sweep:inventory-hygiene", "severity:warning"]


class SweepLibUnavailable(RuntimeError):
    """Raised when sweep_lib is required but unavailable."""


def _load_sweep_lib() -> dict[str, Any]:
    sweep_root = Path(os.environ.get("HERMES_SWEEP_LIB", Path.home() / ".hermes" / "sweep"))
    sys.path.insert(0, str(sweep_root))
    try:
        from lib import (  # type: ignore[import-not-found]
            FindingsDB,
            make_fingerprint,
            record_sweep_run,
            validate_issue_payload,
        )
    except Exception as exc:  # pragma: no cover - exercised through require_sweep_lib
        raise SweepLibUnavailable(f"sweep_lib unavailable at {sweep_root}: {exc}") from exc
    return {
        "FindingsDB": FindingsDB,
        "make_fingerprint": make_fingerprint,
        "record_sweep_run": record_sweep_run,
        "validate_issue_payload": validate_issue_payload,
    }


def _dry_run_fingerprint(normalized_error: str) -> str:
    """Deterministic dry-run fingerprint without importing live sweep_lib."""
    raw = "|".join([SWEEP_ID, TARGET, CHECK_ID, normalized_error, "warning"])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def normalize_error(findings: list[dict[str, object]]) -> str:
    """Stable normalized finding summary for one deduped sweep issue."""
    parts = []
    for finding in sorted(findings, key=lambda item: str(item.get("id", ""))):
        parts.append(f"{finding.get('id')}: {finding.get('evidence')}")
    return " | ".join(" ".join(part.split()).strip().lower() for part in parts)


def issue_title(findings: list[dict[str, object]]) -> str:
    ids = ", ".join(str(f.get("id")) for f in findings[:3])
    suffix = "" if len(findings) <= 3 else f" +{len(findings) - 3} more"
    return f"[Inventory Hygiene] LifeOS doc entrypoint freshness drift: {ids}{suffix}"[:190]


def issue_body(findings: list[dict[str, object]]) -> str:
    evidence_lines = []
    next_actions = []
    for finding in findings:
        raw_paths = finding.get("paths", [])
        paths = raw_paths if isinstance(raw_paths, list) else []
        evidence_lines.append(
            "- {id}: paths={paths}; evidence={evidence}; authority={authority}".format(
                id=finding.get("id"),
                paths=", ".join(str(path) for path in paths),
                evidence=finding.get("evidence"),
                authority=finding.get("authority_class"),
            )
        )
        recovery = str(finding.get("recommended_recovery", "")).strip()
        if recovery and recovery not in next_actions:
            next_actions.append(recovery)
    return (
        "**Finding:** LifeOS README/operator entrypoint freshness drift was detected.\n\n"
        f"**Target:** {TARGET}\n\n"
        "**Evidence:**\n```text\n" + "\n".join(evidence_lines)[:1800] + "\n```\n\n"
        "**Next action:** "
        + "; ".join(next_actions)[:1200]
        + (
            f"\n\nSweep: `{SWEEP_ID}`. Check: `{CHECK_ID}`. "
            "Authority: read-only detector; no docs were modified."
        )
    )


def _as_int(value: object) -> int:
    return value if isinstance(value, int) else 0


def gh_create_issue(repo: str, title: str, body: str, labels: list[str]) -> int:
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as handle:
        handle.write(body)
        body_path = handle.name
    try:
        cmd = ["gh", "issue", "create", "-R", repo, "--title", title, "--body-file", body_path]
        for label in labels:
            cmd.extend(["--label", label])
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=90)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
        url = proc.stdout.strip().splitlines()[-1]
        match = re.search(r"/issues/(\d+)", url)
        if not match:
            raise RuntimeError(f"could not parse issue number from gh output: {url}")
        return int(match.group(1))
    finally:
        try:
            os.unlink(body_path)
        except OSError:
            pass


def process_findings(
    findings: list[dict[str, object]],
    *,
    repo: str = DEFAULT_REPO,
    create_issue: bool = False,
    dry_run: bool = False,
    sweep_lib: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Process detector findings through sweep_lib dedupe semantics."""
    if not findings:
        return {"findings": 0, "findings_created": 0, "findings_updated": 0, "rows": []}

    normalized = normalize_error(findings)
    title = issue_title(findings)
    body = issue_body(findings)
    labels = list(DEFAULT_LABELS)

    if dry_run:
        if sweep_lib is None:
            fingerprint = _dry_run_fingerprint(normalized)
        else:
            sweep_lib["validate_issue_payload"](title, body, labels)
            fingerprint = sweep_lib["make_fingerprint"](
                SWEEP_ID, TARGET, CHECK_ID, normalized, "warning"
            )
        return {
            "findings": len(findings),
            "findings_created": 0,
            "findings_updated": 0,
            "rows": [
                {
                    "fingerprint": fingerprint,
                    "severity": "warning",
                    "title": title,
                    "issue": None,
                    "action": "dry-run",
                }
            ],
        }

    libs = sweep_lib or _load_sweep_lib()
    fingerprint = libs["make_fingerprint"](SWEEP_ID, TARGET, CHECK_ID, normalized, "warning")
    libs["validate_issue_payload"](title, body, labels)

    row = {
        "fingerprint": fingerprint,
        "severity": "warning",
        "title": title,
        "issue": None,
    }

    db = libs["FindingsDB"]()
    try:
        result = db.upsert_finding(fingerprint, SWEEP_ID, TARGET, CHECK_ID, normalized, "warning")
        action = result["action"]
        issue_num = None
        created = 0
        updated = 0
        if action == "created":
            if create_issue:
                issue_num = gh_create_issue(repo, title, body, labels)
                db.upsert_finding(
                    fingerprint,
                    SWEEP_ID,
                    TARGET,
                    CHECK_ID,
                    normalized,
                    "warning",
                    gh_issue_number=issue_num,
                )
            created = 1
        elif action == "updated":
            updated = 1
        row.update({"action": action, "issue": issue_num})
        return {
            "findings": len(findings),
            "findings_created": created,
            "findings_updated": updated,
            "rows": [row],
        }
    finally:
        close = getattr(db, "close", None)
        if callable(close):
            close()


def run(
    repo_root: str | Path,
    *,
    repo: str = DEFAULT_REPO,
    create_issue: bool = False,
    dry_run: bool = False,
    json_output: bool = False,
    record_run: bool = False,
) -> dict[str, object]:
    if dry_run and record_run:
        raise ValueError("record_run mutates sweep receipts and cannot be combined with dry_run")

    findings = check_entrypoint_freshness(repo_root)
    libs = None if dry_run else _load_sweep_lib()
    result = process_findings(
        findings,
        repo=repo,
        create_issue=create_issue,
        dry_run=dry_run,
        sweep_lib=libs,
    )
    receipt = None
    if record_run:
        assert libs is not None
        receipt = libs["record_sweep_run"](
            SWEEP_ID,
            0,
            findings_created=_as_int(result.get("findings_created", 0)),
            findings_updated=_as_int(result.get("findings_updated", 0)),
            telegram_sent=False,
            model_used="no_agent:doc-entrypoint-freshness",
        )
    payload = {
        "sweep_id": SWEEP_ID,
        "target": TARGET,
        "check_id": CHECK_ID,
        "receipt": receipt,
        **result,
    }
    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif findings:
        print(f"{CHECK_ID}: {len(findings)} finding(s)")
    else:
        print("[SILENT]")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_root", help="LifeOS repository root")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="do not mutate sweep findings DB or GitHub",
    )
    parser.add_argument(
        "--create-issue",
        action="store_true",
        help="create one deduped GitHub issue for a new finding",
    )
    parser.add_argument(
        "--record-run",
        action="store_true",
        help="write a sweep_lib run receipt; rejected with --dry-run",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.dry_run and args.record_run:
        parser.error("--record-run mutates sweep receipts and cannot be combined with --dry-run")
    run(
        args.repo_root,
        repo=args.repo,
        create_issue=args.create_issue,
        dry_run=args.dry_run,
        json_output=args.json,
        record_run=args.record_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
