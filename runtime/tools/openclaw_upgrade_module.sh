#!/usr/bin/env bash
set -euo pipefail

if [ -n "${LIFEOS_BUILD_REPO:-}" ]; then
  REPO_ROOT="$LIFEOS_BUILD_REPO"
else
  REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi

DEFAULT_OUT="$REPO_ROOT/artifacts/status/openclaw_upgrade_status.json"
COMMAND="${1:-}"
CHANNEL="stable"
OUT_PATH="$DEFAULT_OUT"

usage() {
  cat <<'EOF'
Usage:
  runtime/tools/openclaw_upgrade_module.sh check [--channel stable|beta|dev]
  runtime/tools/openclaw_upgrade_module.sh propose [--channel stable|beta|dev]
  runtime/tools/openclaw_upgrade_module.sh report [--channel stable|beta|dev] [--out <path>]

Commands:
  check     Emit current OpenClaw upgrade status as JSON (non-mutating).
  propose   Emit status plus pinned recommended apply command as JSON (non-mutating).
  report    Emit status JSON and write it to artifacts/status (or --out path).

Notes:
  - Retries transient registry failures, then falls back to cached dist-tags if available.
  - Fail-closed when both live registry and cache are unavailable (exit code 2).
  - This module never executes upgrades; it only reports/proposes.
EOF
}

if [ -z "$COMMAND" ]; then
  usage
  exit 2
fi
shift || true

while [ "$#" -gt 0 ]; do
  case "$1" in
    --channel)
      if [ "$#" -lt 2 ]; then
        echo "ERROR: --channel requires a value." >&2
        exit 2
      fi
      CHANNEL="$2"
      shift 2
      ;;
    --out)
      if [ "$#" -lt 2 ]; then
        echo "ERROR: --out requires a value." >&2
        exit 2
      fi
      OUT_PATH="$2"
      shift 2
      ;;
    -h|--help|help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

case "$COMMAND" in
  check|propose|report) ;;
  *)
    echo "ERROR: Unknown command: $COMMAND" >&2
    usage
    exit 2
    ;;
esac

python3 - "$COMMAND" "$CHANNEL" "$OUT_PATH" <<'PY'
from __future__ import annotations

import os
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _run(cmd: list[str], timeout_s: int = 25) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except FileNotFoundError:
        return 127, "", "command_not_found"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout_after_{timeout_s}s"
    except Exception as exc:
        return 1, "", f"subprocess_error:{type(exc).__name__}:{exc}"
    return int(proc.returncode), (proc.stdout or "").strip(), (proc.stderr or "").strip()


def _safe_json(raw: str) -> Any:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _first_nonempty_line(*texts: str) -> str:
    for text in texts:
        for line in (text or "").splitlines():
            candidate = line.strip()
            if candidate:
                return candidate
    return ""


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return max(default, minimum)
    return max(value, minimum)


def _env_float(name: str, default: float, minimum: float = 0.0) -> float:
    raw = os.environ.get(name, str(default))
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return max(default, minimum)
    return max(value, minimum)


def _normalize_dist_tags(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    tags = {str(k): str(v) for k, v in raw.items() if str(v).strip()}
    return tags or None


def _load_cached_dist_tags(cache_path: str) -> tuple[dict[str, str] | None, str]:
    path = Path(cache_path)
    if not path.exists():
        return None, "cache_missing"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"cache_read_error:{type(exc).__name__}"
    payload = _safe_json(text)
    if not isinstance(payload, dict):
        return None, "cache_invalid_json"
    tags = _normalize_dist_tags(payload.get("registry_dist_tags"))
    if not tags:
        return None, "cache_tags_missing"
    return tags, ""


def _registry_dist_tags(
    *,
    timeout_s: int,
    retries: int,
    retry_delay_s: float,
    cache_path: str,
) -> tuple[dict[str, str] | None, dict[str, Any]]:
    errors: list[str] = []
    for attempt in range(1, retries + 1):
        rc_tags, out_tags, err_tags = _run(
            ["npm", "view", "openclaw", "dist-tags", "--json"],
            timeout_s=timeout_s,
        )
        parsed_tags = _safe_json(out_tags)
        tags = _normalize_dist_tags(parsed_tags)
        if rc_tags == 0 and tags:
            return tags, {
                "ok": True,
                "error": "",
                "attempts": attempt,
                "source": "live",
            }

        err_line = _first_nonempty_line(err_tags, out_tags) or f"npm_rc_{rc_tags}"
        if rc_tags == 0 and not tags:
            err_line = "dist_tags_unparsed_or_empty"
        errors.append(err_line)
        if attempt < retries and retry_delay_s > 0:
            time.sleep(retry_delay_s)

    cached_tags, cache_error = _load_cached_dist_tags(cache_path)
    if cached_tags:
        fallback_error = errors[-1] if errors else "registry_lookup_failed"
        return cached_tags, {
            "ok": True,
            "error": "",
            "attempts": retries,
            "source": "cache",
            "warning": f"using_cached_dist_tags_after_live_failure:{fallback_error}",
        }

    return None, {
        "ok": False,
        "error": errors[-1] if errors else "registry_lookup_failed",
        "attempts": retries,
        "source": "none",
        "cache_error": cache_error,
    }


def _parse_version(value: str | None) -> tuple[list[int], int]:
    text = (value or "").strip()
    if not text:
        return ([], 0)
    main, has_dash, _pre = text.partition("-")
    nums: list[int] = []
    for part in main.split("."):
        part = part.strip()
        if part.isdigit():
            nums.append(int(part))
        else:
            break
    while len(nums) < 3:
        nums.append(0)
    # Stable releases rank above pre-release tags with the same numeric version.
    stable_weight = 1 if has_dash == "" else 0
    return nums, stable_weight


def _compare_versions(installed: str | None, target: str | None) -> str:
    if not installed or not target:
        return "unknown"
    i_nums, i_stable = _parse_version(installed)
    t_nums, t_stable = _parse_version(target)
    if not i_nums or not t_nums:
        return "unknown"
    if i_nums < t_nums:
        return "behind"
    if i_nums > t_nums:
        return "ahead"
    if i_stable < t_stable:
        return "behind"
    if i_stable > t_stable:
        return "ahead"
    return "up_to_date"


def _extract_channel_value(update_status_json: Any) -> str | None:
    if not isinstance(update_status_json, dict):
        return None
    channel = update_status_json.get("channel")
    if not isinstance(channel, dict):
        return None
    val = channel.get("value")
    if isinstance(val, str) and val.strip():
        return val.strip()
    return None


def _coo_health() -> dict[str, Any]:
    rc, out, err = _run(["coo", "models", "status"], timeout_s=30)
    text = "\n".join(part for part in [out, err] if part).strip()
    status_line = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("STATUS:"):
            status_line = stripped
            break
    if not status_line:
        status_line = _first_nonempty_line(out, err)

    health_pass: bool | None
    reason: str
    upper_text = text.upper()
    if "STATUS: VALID" in upper_text:
        health_pass = True
        reason = "valid"
    elif "STATUS: OK" in upper_text:
        health_pass = True
        reason = "ok"
    elif "STATUS: INVALID" in upper_text:
        health_pass = False
        reason = "invalid"
    elif rc == 127:
        health_pass = None
        reason = "coo_not_found"
    elif rc != 0:
        health_pass = None
        reason = f"coo_status_failed_rc_{rc}"
    else:
        health_pass = None
        reason = "status_unparsed"

    return {
        "checked": rc != 127,
        "pass": health_pass,
        "reason": reason,
        "exit_code": rc,
        "status_line": status_line,
        "command": "coo models status",
    }


def main() -> int:
    if len(sys.argv) != 4:
        print("{}", end="")
        return 2

    command, requested_channel, out_path_raw = sys.argv[1], sys.argv[2], sys.argv[3]
    npm_timeout_s = _env_int("OPENCLAW_UPGRADE_NPM_TIMEOUT_SEC", 45, minimum=1)
    npm_retries = _env_int("OPENCLAW_UPGRADE_NPM_RETRIES", 3, minimum=1)
    npm_retry_delay_s = _env_float("OPENCLAW_UPGRADE_NPM_RETRY_DELAY_SEC", 1.0, minimum=0.0)
    if requested_channel not in {"stable", "beta", "dev"}:
        print(
            json.dumps(
                {
                    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                    "channel": requested_channel,
                    "registry_check": {"ok": False, "error": "invalid_channel"},
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2

    checked_at = datetime.now(timezone.utc).isoformat()
    payload: dict[str, Any] = {
        "checked_at_utc": checked_at,
        "channel": requested_channel,
        "command": command,
        "installed_version": None,
        "registry_latest": None,
        "registry_dist_tags": {},
        "registry_source": "none",
        "registry_check": {"ok": False, "error": ""},
        "version_comparison": "unknown",
        "update_available": None,
        "recommended_apply_command": None,
        "recommended_validation_command": "runtime/tools/openclaw_coo_update_protocol.sh all-preclose",
        "recommended_verify_command_template": "runtime/tools/openclaw_coo_update_protocol.sh promotion-verify --packet-dir <dir>",
        "recommended_record_command_template": "runtime/tools/openclaw_coo_update_protocol.sh promotion-run --packet-dir <dir>",
        "health_gate": _coo_health(),
        "needs_action": None,
        "status_report_path": str(out_path_raw) if command == "report" else None,
    }

    # Installed CLI version.
    rc_version, out_version, err_version = _run(["openclaw", "--version"], timeout_s=10)
    if rc_version == 0:
        payload["installed_version"] = _first_nonempty_line(out_version, err_version) or None
    else:
        payload["installed_version"] = None

    # Optional channel introspection from OpenClaw status if available.
    rc_ch, out_ch, _err_ch = _run(["openclaw", "update", "status", "--json"], timeout_s=15)
    if rc_ch == 0:
        parsed_ch = _safe_json(out_ch)
        detected = _extract_channel_value(parsed_ch)
        if detected:
            payload["detected_channel"] = detected

    # Registry check retries transient failures and falls back to cached tags.
    tags, registry_check = _registry_dist_tags(
        timeout_s=npm_timeout_s,
        retries=npm_retries,
        retry_delay_s=npm_retry_delay_s,
        cache_path=out_path_raw,
    )
    payload["registry_check"] = registry_check
    payload["registry_source"] = str(registry_check.get("source", "none"))
    if tags:
        payload["registry_dist_tags"] = tags
        tag_map = {"stable": "latest", "beta": "beta", "dev": "dev"}
        target_key = tag_map[requested_channel]
        target_value = tags.get(target_key)
        if not target_value:
            payload["registry_check"] = {
                **payload["registry_check"],
                "ok": False,
                "error": f"dist_tag_missing:{target_key}",
            }
        else:
            payload["registry_latest"] = target_value

    payload["version_comparison"] = _compare_versions(payload.get("installed_version"), payload.get("registry_latest"))
    comparison = payload["version_comparison"]
    if comparison == "behind":
        payload["update_available"] = True
    elif comparison in {"up_to_date", "ahead"}:
        payload["update_available"] = False
    else:
        payload["update_available"] = None

    if payload["update_available"] is True and payload.get("registry_latest"):
        payload["recommended_apply_command"] = f"npm install -g openclaw@{payload['registry_latest']}"

    health_pass = (payload.get("health_gate") or {}).get("pass")
    update_available = payload.get("update_available")
    payload["needs_action"] = bool(update_available is True or health_pass is False)

    if command == "propose":
        head_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=False, timeout=10,
        ).stdout.strip() or None
        payload["promotion_packet_base"] = {
            "target_commit": head_sha,
            "target_version": payload.get("registry_latest"),
            "previous_version": payload.get("installed_version"),
        }
        payload["proposal"] = {
            "apply_then_record": [
                payload.get("recommended_apply_command"),
                "openclaw --version",
                payload.get("recommended_verify_command_template"),
                payload.get("recommended_record_command_template"),
            ]
            if payload.get("recommended_apply_command")
            else [
                payload.get("recommended_verify_command_template"),
                payload.get("recommended_record_command_template"),
            ],
            "mode": "manual_apply_then_record",
        }

    if command == "report":
        out_path = Path(out_path_raw)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2, sort_keys=True))
    if payload.get("registry_check", {}).get("ok") is not True:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY
