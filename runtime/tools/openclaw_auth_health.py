#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence, Tuple

# Ensure repo root is importable when script is executed directly.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.tools.schemas import AuthHealthResult

COOLDOWN_RE = re.compile(r"(in cooldown|all profiles unavailable|profiles are unavailable)", re.IGNORECASE)
INVALID_MISSING_RE = re.compile(
    r"(expired|missing|invalid|unauthorized|not authenticated|authentication required|token has been invalidated)",
    re.IGNORECASE,
)
EXPIRING_RE = re.compile(r"(expiring soon|expires in\s*[0-9]+(?:m|h))", re.IGNORECASE)
PROVIDER_RE = re.compile(r"\bprovider\s+([a-z0-9._-]+)\b", re.IGNORECASE)
PROVIDER_COOLDOWN_RE = re.compile(r"\bprovider\s+([a-z0-9._-]+)\s+is\s+in\s+cooldown\b", re.IGNORECASE)


def ts_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_run(cmd: Sequence[str], timeout_s: int = 30) -> Tuple[int, str]:
    try:
        proc = subprocess.run(
            list(cmd),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except Exception as exc:
        return 1, f"subprocess_error:{type(exc).__name__}:{exc}"

    merged = "\n".join(
        [
            (proc.stdout or "").strip(),
            (proc.stderr or "").strip(),
        ]
    ).strip()
    return int(proc.returncode), merged


def detect_provider(output_text: str) -> str:
    text = str(output_text or "")
    match = PROVIDER_COOLDOWN_RE.search(text) or PROVIDER_RE.search(text)
    if match:
        provider = str(match.group(1) or "").strip().lower()
        if provider:
            return provider
    return "multi-provider"


def classify_auth_health(exit_code: int, output_text: str) -> AuthHealthResult:
    text = str(output_text or "")
    low = text.lower()
    provider = detect_provider(text)
    now = ts_utc()

    if exit_code == 0:
        if EXPIRING_RE.search(text):
            return AuthHealthResult(
                provider=provider,
                state="expiring",
                reason_code="expiring_warning",
                recommended_action="refresh auth within 24h",
                ts_utc=now,
            )
        return AuthHealthResult(
            provider=provider,
            state="ok",
            reason_code="ok",
            recommended_action="none",
            ts_utc=now,
        )

    if COOLDOWN_RE.search(text):
        return AuthHealthResult(
            provider=provider,
            state="cooldown",
            reason_code="provider_cooldown",
            recommended_action="wait cooldown or add backup profile",
            ts_utc=now,
        )

    if exit_code == 2 or EXPIRING_RE.search(text):
        return AuthHealthResult(
            provider=provider,
            state="expiring",
            reason_code="expiring_nonzero",
            recommended_action="refresh auth within 24h",
            ts_utc=now,
        )

    if exit_code == 1 or INVALID_MISSING_RE.search(low):
        return AuthHealthResult(
            provider=provider,
            state="invalid_missing",
            reason_code="expired_or_missing",
            recommended_action="re-auth affected provider profile",
            ts_utc=now,
        )

    return AuthHealthResult(
        provider=provider,
        state="invalid_missing",
        reason_code=f"check_failed_rc_{exit_code}",
        recommended_action="inspect models status and re-auth provider profiles",
        ts_utc=now,
    )


def append_auth_health_record(path: Path, result: AuthHealthResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = result.to_dict()
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        fh.write("\n")


def run_auth_health_check(openclaw_bin: str, timeout_s: int) -> Tuple[int, str]:
    cmd = [openclaw_bin, "models", "status", "--check"]
    return _safe_run(cmd, timeout_s=timeout_s)


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify OpenClaw auth health from models status checks.")
    parser.add_argument("--openclaw-bin", default=os.environ.get("OPENCLAW_BIN", "openclaw"))
    parser.add_argument("--state-dir", default=os.environ.get("OPENCLAW_STATE_DIR", str(Path.home() / ".openclaw")))
    parser.add_argument("--timeout-sec", type=int, default=30)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    rc, merged = run_auth_health_check(args.openclaw_bin, timeout_s=max(1, int(args.timeout_sec)))
    result = classify_auth_health(rc, merged)

    out_path = Path(args.state_dir).expanduser() / "runtime" / "gates" / "auth_health.jsonl"
    try:
        append_auth_health_record(out_path, result)
    except Exception as exc:
        error_payload = {
            "state": "invalid_missing",
            "reason_code": "auth_health_append_failed",
            "error_detail": f"{type(exc).__name__}:{exc}",
            "provider": result.provider,
            "ts_utc": result.ts_utc,
        }
        if args.json:
            print(json.dumps(error_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        else:
            print(
                f"state={error_payload['state']} reason_code={error_payload['reason_code']} "
                f"provider={result.provider} ts_utc={result.ts_utc}"
            )
        return 1

    payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(
            f"state={result.state} reason_code={result.reason_code} "
            f"provider={result.provider} ts_utc={result.ts_utc}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
