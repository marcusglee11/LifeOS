#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

ALLOWED_CLASSIFICATIONS = {"PUBLIC", "INTERNAL", "CONFIDENTIAL"}
RETENTION_RE = re.compile(r"^(?:\d+(?:d|w|m|y)|permanent)$", re.IGNORECASE)

KEYWORD_PATTERNS = [
    re.compile(r"\bapiKey\b", re.IGNORECASE),
    re.compile(r"\bbotToken\b", re.IGNORECASE),
    re.compile(r"\bsigningSecret\b", re.IGNORECASE),
    re.compile(r"Authorization\s*:\s*Bearer\s+\S+", re.IGNORECASE),
]
TOKEN_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{8,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
]
LONG_BLOB_RE = re.compile(r"[A-Za-z0-9+/_=-]{80,}")


@dataclass
class Violation:
    file: str
    line: int
    rule: str
    message: str
    snippet: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "file": self.file,
            "line": self.line,
            "rule": self.rule,
            "message": self.message,
            "snippet": self.snippet,
        }


def redact_line(line: str) -> str:
    out = line.rstrip("\n")
    out = re.sub(r"Authorization\s*:\s*Bearer\s+\S+", "Authorization: Bearer [REDACTED]", out, flags=re.IGNORECASE)
    out = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}\b", "sk-[REDACTED]", out)
    out = re.sub(r"\bxox[baprs]-[A-Za-z0-9-]{8,}\b", "xox?- [REDACTED]", out)
    out = re.sub(r"\bghp_[A-Za-z0-9]{20,}\b", "ghp_[REDACTED]", out)
    out = re.sub(r"\bAIza[0-9A-Za-z_-]{20,}\b", "AIza[REDACTED]", out)
    out = LONG_BLOB_RE.sub("[REDACTED_LONG_BLOB]", out)
    out = re.sub(r"\b(apiKey|botToken|signingSecret)\b\s*[:=]\s*\S+", r"\1=[REDACTED]", out, flags=re.IGNORECASE)
    return out


def parse_front_matter(lines: List[str]) -> Tuple[Optional[Dict[str, str]], int]:
    if not lines or lines[0].strip() != "---":
        return None, 0
    fm: Dict[str, str] = {}
    idx = 1
    while idx < len(lines):
        raw = lines[idx]
        if raw.strip() == "---":
            return fm, idx + 1
        if ":" in raw:
            key, value = raw.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key:
                fm[key] = value
        idx += 1
    return None, 0


def iter_memory_files(workspace: Path) -> Iterable[Path]:
    memory_md = workspace / "MEMORY.md"
    if memory_md.exists():
        yield memory_md
    memory_dir = workspace / "memory"
    if memory_dir.exists():
        for path in sorted(memory_dir.rglob("*.md")):
            if path.is_file():
                yield path


def detect_secret_like(text: str, line: str) -> bool:
    return any(p.search(text) for p in KEYWORD_PATTERNS + TOKEN_PATTERNS) or bool(LONG_BLOB_RE.search(line))


def scan_workspace(workspace: Path) -> Dict[str, object]:
    violations: List[Violation] = []
    scanned_files = 0
    memory_entry_files = 0

    for path in iter_memory_files(workspace):
        scanned_files += 1
        rel = str(path.relative_to(workspace))
        content = path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        # Secret/token-like detection applies to all memory files, including MEMORY.md.
        for i, line in enumerate(lines, start=1):
            if detect_secret_like(line, line):
                violations.append(
                    Violation(
                        file=rel,
                        line=i,
                        rule="SECRET_PATTERN_BLOCKED",
                        message="Secret-like content detected; memory indexing is blocked.",
                        snippet=redact_line(line),
                    )
                )

        # Enforce metadata schema for memory entry files only.
        if rel.startswith("memory/"):
            memory_entry_files += 1
            fm, _ = parse_front_matter(lines)
            if fm is None:
                violations.append(
                    Violation(
                        file=rel,
                        line=1,
                        rule="MISSING_FRONT_MATTER",
                        message="Memory entry must start with YAML front matter.",
                        snippet=redact_line(lines[0] if lines else ""),
                    )
                )
                continue

            classification = (fm.get("classification") or "").strip().upper()
            if not classification:
                violations.append(
                    Violation(
                        file=rel,
                        line=1,
                        rule="MISSING_CLASSIFICATION",
                        message="classification is required in front matter.",
                        snippet="classification: [MISSING]",
                    )
                )
            elif classification == "SECRET":
                violations.append(
                    Violation(
                        file=rel,
                        line=1,
                        rule="CLASSIFICATION_SECRET_DISALLOWED",
                        message="classification SECRET is disallowed for memory storage.",
                        snippet="classification: SECRET",
                    )
                )
            elif classification not in ALLOWED_CLASSIFICATIONS:
                violations.append(
                    Violation(
                        file=rel,
                        line=1,
                        rule="INVALID_CLASSIFICATION",
                        message=f"classification must be one of {sorted(ALLOWED_CLASSIFICATIONS)}.",
                        snippet=f"classification: {classification}",
                    )
                )

            retention = (fm.get("retention") or "").strip()
            if not retention:
                violations.append(
                    Violation(
                        file=rel,
                        line=1,
                        rule="MISSING_RETENTION",
                        message="retention is required in front matter.",
                        snippet="retention: [MISSING]",
                    )
                )
            elif not RETENTION_RE.match(retention):
                violations.append(
                    Violation(
                        file=rel,
                        line=1,
                        rule="INVALID_RETENTION",
                        message='retention must match ^\\d+(d|w|m|y)$ or "permanent".',
                        snippet=f"retention: {retention}",
                    )
                )

    summary = {
        "workspace": str(workspace),
        "scanned_files": scanned_files,
        "memory_entry_files": memory_entry_files,
        "violations_count": len(violations),
        "policy_ok": len(violations) == 0,
        "violations": [v.to_dict() for v in violations],
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw memory policy guard.")
    parser.add_argument("--workspace", default=str(Path.home() / ".openclaw" / "workspace"))
    parser.add_argument("--json-summary", action="store_true", help="Print JSON summary only.")
    parser.add_argument("--summary-out", help="Write JSON summary to this path.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser()
    summary = scan_workspace(workspace)

    if args.summary_out:
        out = Path(args.summary_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    if args.json_summary:
        print(json.dumps(summary, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(
            f"memory_policy_ok={'true' if summary['policy_ok'] else 'false'} "
            f"scanned_files={summary['scanned_files']} "
            f"memory_entry_files={summary['memory_entry_files']} "
            f"violations={summary['violations_count']}"
        )
        for v in summary["violations"]:
            print(f"- {v['file']}:{v['line']} [{v['rule']}] {v['message']} :: {v['snippet']}")

    return 0 if summary["policy_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
