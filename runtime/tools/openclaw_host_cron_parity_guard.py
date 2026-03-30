#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

BEGIN_RE = re.compile(r"^\s*#\s*OPENCLAW_PARITY_BEGIN\s+instance=([^\s]+)\s+job=([^\s]+)\s*$")
END_RE = re.compile(r"^\s*#\s*OPENCLAW_PARITY_END\s*$")


@dataclass
class ParsedEntry:
    instance_id: str
    job_type: str
    schedule: str
    command: str
    line_no: int

    @property
    def key(self) -> str:
        return f"{self.instance_id}:{self.job_type}"


def ts_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_cron_line(line: str) -> Optional[Tuple[str, str]]:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    parts = stripped.split()
    if len(parts) < 6:
        return None
    schedule = " ".join(parts[:5])
    command = " ".join(parts[5:])
    return schedule, command


def parse_managed_entries(crontab_text: str) -> Tuple[List[ParsedEntry], List[str]]:
    entries: List[ParsedEntry] = []
    violations: List[str] = []

    active_instance = ""
    active_job = ""
    active_start = 0
    active_lines: List[Tuple[int, str]] = []

    lines = crontab_text.splitlines()
    for idx, line in enumerate(lines, start=1):
        begin = BEGIN_RE.match(line)
        if begin:
            if active_instance:
                violations.append(f"nested_managed_block line={idx}")
            active_instance = begin.group(1).strip()
            active_job = begin.group(2).strip()
            active_start = idx
            active_lines = []
            continue

        if END_RE.match(line):
            if not active_instance:
                violations.append(f"orphan_managed_block_end line={idx}")
                continue
            cron_lines = [item for item in active_lines if _parse_cron_line(item[1]) is not None]
            if len(cron_lines) != 1:
                violations.append(
                    f"managed_block_entry_count_invalid instance={active_instance} job={active_job} count={len(cron_lines)} start={active_start}"
                )
            else:
                line_no, cron_line = cron_lines[0]
                parsed = _parse_cron_line(cron_line)
                if parsed is None:
                    violations.append(
                        f"managed_block_line_parse_failed instance={active_instance} job={active_job} line={line_no}"
                    )
                else:
                    schedule, command = parsed
                    entries.append(
                        ParsedEntry(
                            instance_id=active_instance,
                            job_type=active_job,
                            schedule=schedule,
                            command=command,
                            line_no=line_no,
                        )
                    )
            active_instance = ""
            active_job = ""
            active_start = 0
            active_lines = []
            continue

        if active_instance:
            active_lines.append((idx, line))

    if active_instance:
        violations.append(
            f"managed_block_missing_end instance={active_instance} job={active_job} start={active_start}"
        )

    return entries, violations


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def evaluate(entries: List[ParsedEntry], profile: dict) -> dict:
    violations: List[str] = []
    rows: List[dict] = []

    expected_jobs = profile.get("parity_jobs") or []
    if not isinstance(expected_jobs, list):
        expected_jobs = []

    expected_by_key: Dict[str, dict] = {}
    for item in expected_jobs:
        if not isinstance(item, dict):
            continue
        instance_id = str(item.get("instance_id") or profile.get("instance_id") or "").strip()
        job_type = str(item.get("job_type") or "").strip()
        if not instance_id or not job_type:
            continue
        expected_by_key[f"{instance_id}:{job_type}"] = item

    seen_keys: Dict[str, int] = {}
    for entry in entries:
        seen_keys[entry.key] = seen_keys.get(entry.key, 0) + 1
        rows.append(
            {
                "instance_id": entry.instance_id,
                "job_type": entry.job_type,
                "schedule": entry.schedule,
                "command": entry.command,
                "line_no": entry.line_no,
            }
        )

    for key, count in sorted(seen_keys.items()):
        if count != 1:
            violations.append(f"duplicate_entry_key key={key} count={count}")

    for key, exp in sorted(expected_by_key.items()):
        matching = [e for e in entries if e.key == key]
        if len(matching) != 1:
            violations.append(f"missing_or_duplicate_expected_key key={key} count={len(matching)}")
            continue
        entry = matching[0]

        expected_schedule = str(exp.get("schedule") or "").strip()
        if expected_schedule and entry.schedule != expected_schedule:
            violations.append(
                f"schedule_mismatch key={key} expected={expected_schedule} got={entry.schedule}"
            )

        wrapper_path = str(exp.get("wrapper_path") or "").strip()
        if wrapper_path:
            wrapper_abs = os.path.abspath(os.path.expanduser(wrapper_path))
            if wrapper_abs not in entry.command:
                violations.append(f"wrapper_path_missing_in_command key={key}")
            wrapper_sha = str(exp.get("wrapper_sha256") or "").strip().lower()
            if wrapper_sha:
                p = Path(wrapper_abs)
                if not p.exists():
                    violations.append(f"wrapper_missing key={key} path={wrapper_abs}")
                else:
                    actual = _hash_file(p)
                    if actual != wrapper_sha:
                        violations.append(
                            f"wrapper_hash_mismatch key={key} expected={wrapper_sha} got={actual}"
                        )

    expected_user = str(profile.get("run_user") or "").strip()
    current_user = getpass.getuser()
    if expected_user and expected_user != current_user:
        violations.append(f"run_user_mismatch expected={expected_user} got={current_user}")

    return {
        "pass": len(violations) == 0,
        "violations": violations,
        "entries": rows,
        "expected_keys": sorted(expected_by_key.keys()),
        "seen_keys": sorted(seen_keys.keys()),
        "run_user": current_user,
    }


def _read_crontab_text(crontab_file: str) -> Tuple[str, int, str]:
    if crontab_file:
        p = Path(crontab_file)
        text = p.read_text(encoding="utf-8", errors="replace")
        return text, 0, ""

    proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip().lower()
        if "no crontab" in stderr:
            return "", 0, ""
    return proc.stdout or "", int(proc.returncode), (proc.stderr or "").strip()[:500]


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed host cron parity guard.")
    parser.add_argument("--instance-profile", default="config/openclaw/instance_profiles/coo.json")
    parser.add_argument(
        "--crontab-file", default="", help="Optional test input file instead of `crontab -l`."
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = {
        "ts_utc": ts_utc(),
        "instance_profile": args.instance_profile,
        "crontab_file": args.crontab_file,
        "pass": False,
        "violations": [],
        "entries": [],
    }

    profile_path = Path(args.instance_profile).expanduser()
    if not profile_path.exists():
        result["violations"] = [f"instance_profile_missing:{profile_path}"]
    else:
        try:
            profile = _safe_load_json(profile_path)
        except Exception as exc:
            result["violations"] = [f"instance_profile_invalid:{type(exc).__name__}"]
            profile = {}

        text, rc, stderr = _read_crontab_text(args.crontab_file)
        result["crontab_rc"] = rc
        if stderr:
            result["crontab_stderr"] = stderr

        if rc != 0:
            result["violations"] = ["crontab_list_failed"]
        else:
            entries, parse_violations = parse_managed_entries(text)
            evaluated = evaluate(entries, profile)
            result["entries"] = evaluated["entries"]
            result["expected_keys"] = evaluated["expected_keys"]
            result["seen_keys"] = evaluated["seen_keys"]
            result["run_user"] = evaluated["run_user"]
            result["violations"] = parse_violations + evaluated["violations"]
            result["pass"] = len(result["violations"]) == 0

    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        if result["pass"]:
            print(
                f"PASS host_cron_parity_guard=true expected_keys={len(result.get('expected_keys') or [])} "
                f"entries={len(result.get('entries') or [])}"
            )
        else:
            top = result["violations"][0] if result["violations"] else "unknown_violation"
            print(f"FAIL host_cron_parity_guard=false reason={top}")

    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
