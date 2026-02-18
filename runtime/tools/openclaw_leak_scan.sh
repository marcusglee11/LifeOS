#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: runtime/tools/openclaw_leak_scan.sh <path...>" >&2
  exit 2
fi

python3 - "$@" <<'PY'
from __future__ import annotations
import re
import sys
from pathlib import Path

patterns = [
    ("apiKey", re.compile(r"apiKey\s*[:=]\s*[\"']?[^\"'\s]+", re.I)),
    ("botToken", re.compile(r"botToken\s*[:=]\s*[\"']?[^\"'\s]+", re.I)),
    ("Authorization: Bearer", re.compile(r"Authorization:\s*Bearer\s+\S+", re.I)),
    ("sk-", re.compile(r"\bsk-[A-Za-z0-9_-]{8,}")),
    ("sk-ant-", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{8,}")),
    ("ghu_/gho_/ghp_", re.compile(r"\bgh[opurs]_[A-Za-z0-9]{12,}\b")),
    ("xox*", re.compile(r"\bxox[aboprs]-[A-Za-z0-9-]{8,}\b")),
    ("AIza", re.compile(r"\bAIza[0-9A-Za-z_-]{8,}")),
    ("ya29.", re.compile(r"\bya29\.[0-9A-Za-z._-]{12,}\b")),
    ("base64-ish", re.compile(r"\b[A-Za-z0-9+/=_-]{80,}\b")),
]

failed = False
for raw in sys.argv[1:]:
    path = Path(raw)
    if not path.exists():
        print(f"LEAK_SCAN_MISSING file={path}")
        failed = True
        continue

    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    local_hits = 0
    for lineno, line in enumerate(content, start=1):
        for name, rgx in patterns:
            match = rgx.search(line)
            if not match:
                continue
            local_hits += 1
            failed = True
            redacted = line[: match.start()] + "[REDACTED_MATCH]" + line[match.end() :]
            print(f"LEAK_SCAN_HIT file={path} line={lineno} pattern={name} text={redacted[:220]}")
            break

    if local_hits == 0:
        print(f"LEAK_SCAN_PASS file={path}")

if failed:
    sys.exit(1)
PY
