#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping

SLACK_SECRET_KEYS = ("appToken", "botToken", "signingSecret")
MODE_SOCKET = "socket"
MODE_HTTP = "http"


def utc_ts_compact() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_config(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_dir_0700(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)


def write_json_0600(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def slack_base_posture(cfg: Mapping[str, Any]) -> Dict[str, Any]:
    channels = cfg.get("channels") if isinstance(cfg, Mapping) else {}
    slack = channels.get("slack") if isinstance(channels, Mapping) else None
    if not isinstance(slack, Mapping):
        return {
            "slack_base_present": False,
            "slack_base_enabled": False,
            "slack_base_disabled": True,
            "slack_secrets_in_base": False,
            "slack_secret_key_count": 0,
        }

    secrets = [k for k in SLACK_SECRET_KEYS if str(slack.get(k) or "").strip()]
    enabled = bool(slack.get("enabled") is True)
    return {
        "slack_base_present": True,
        "slack_base_enabled": enabled,
        "slack_base_disabled": not enabled,
        "slack_secrets_in_base": len(secrets) > 0,
        "slack_secret_key_count": len(secrets),
    }


def _required_env(mode: str) -> Dict[str, str]:
    if mode == MODE_SOCKET:
        return {
            "OPENCLAW_SLACK_APP_TOKEN": "xapp-",
            "OPENCLAW_SLACK_BOT_TOKEN": "xoxb-",
        }
    if mode == MODE_HTTP:
        return {
            "OPENCLAW_SLACK_BOT_TOKEN": "xoxb-",
            "OPENCLAW_SLACK_SIGNING_SECRET": "",
        }
    raise ValueError(f"unsupported mode: {mode}")


def validate_env(mode: str, env: Mapping[str, str]) -> Dict[str, bool]:
    required = _required_env(mode)
    presence = {k: bool(str(env.get(k, "")).strip()) for k in required}
    missing = [k for k, present in presence.items() if not present]
    if missing:
        raise ValueError("missing required env: " + ",".join(sorted(missing)))

    malformed = []
    for key, prefix in required.items():
        val = str(env.get(key, ""))
        if prefix and not val.startswith(prefix):
            malformed.append(f"{key}:expected_prefix:{prefix}")
    if malformed:
        raise ValueError("malformed env: " + ",".join(malformed))

    return presence


def generate_overlay_config(base_cfg: Mapping[str, Any], mode: str, env: Mapping[str, str]) -> Dict[str, Any]:
    cfg = copy.deepcopy(dict(base_cfg))
    channels = cfg.get("channels")
    if not isinstance(channels, dict):
        channels = {}
        cfg["channels"] = channels

    slack = channels.get("slack")
    if not isinstance(slack, dict):
        slack = {}
    else:
        slack = dict(slack)

    # Clear any pre-existing secret keys in working copy before injecting env values.
    for key in SLACK_SECRET_KEYS:
        slack.pop(key, None)

    slack["enabled"] = True
    if mode == MODE_SOCKET:
        slack["mode"] = MODE_SOCKET
        slack["appToken"] = str(env["OPENCLAW_SLACK_APP_TOKEN"])
        slack["botToken"] = str(env["OPENCLAW_SLACK_BOT_TOKEN"])
    elif mode == MODE_HTTP:
        slack["mode"] = MODE_HTTP
        slack["webhookPath"] = str(slack.get("webhookPath") or "/slack/events")
        slack["botToken"] = str(env["OPENCLAW_SLACK_BOT_TOKEN"])
        slack["signingSecret"] = str(env["OPENCLAW_SLACK_SIGNING_SECRET"])
    else:
        raise ValueError(f"unsupported mode: {mode}")

    channels["slack"] = slack
    return cfg


def generate_overlay_files(
    base_config_path: Path,
    output_dir: Path,
    mode: str,
    env: Mapping[str, str],
    *,
    created_utc: str | None = None,
) -> Dict[str, Any]:
    base_cfg = load_config(base_config_path)
    posture = slack_base_posture(base_cfg)
    if not posture["slack_base_disabled"]:
        raise ValueError("base config must keep Slack disabled")
    if posture["slack_secrets_in_base"]:
        raise ValueError("base config contains Slack secret fields")

    env_presence = validate_env(mode, env)
    overlay_cfg = generate_overlay_config(base_cfg, mode, env)

    ensure_dir_0700(output_dir)
    ts = created_utc or utc_ts_compact()
    overlay_path = output_dir / "openclaw_slack_overlay.json"
    metadata_path = output_dir / "overlay_metadata.json"

    write_json_0600(overlay_path, overlay_cfg)
    metadata = {
        "created_utc": ts,
        "mode": mode,
        "base_config_path": str(base_config_path),
        "overlay_config_path": str(overlay_path),
        "env_present": env_presence,
        "slack_base_disabled": bool(posture["slack_base_disabled"]),
        "slack_secrets_in_base": bool(posture["slack_secrets_in_base"]),
    }
    write_json_0600(metadata_path, metadata)
    return {
        "overlay_config_path": str(overlay_path),
        "overlay_metadata_path": str(metadata_path),
        "mode": mode,
        "env_present": env_presence,
        "slack_base_disabled": bool(posture["slack_base_disabled"]),
        "slack_secrets_in_base": bool(posture["slack_secrets_in_base"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Slack-enabled OpenClaw overlay config from env-only secrets.")
    parser.add_argument("--base-config", default=os.environ.get("OPENCLAW_CONFIG_PATH", str(Path.home() / ".openclaw" / "openclaw.json")))
    parser.add_argument("--output-dir")
    parser.add_argument("--mode", choices=[MODE_SOCKET, MODE_HTTP], default=None)
    parser.add_argument("--check-base", action="store_true", help="Check base Slack posture only and print redacted-safe summary.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    mode = (args.mode or os.environ.get("OPENCLAW_SLACK_MODE") or MODE_SOCKET).strip().lower()
    base_config_path = Path(args.base_config).expanduser()
    ts = utc_ts_compact()
    default_out = Path.home() / ".openclaw" / "runtime" / "slack_overlay" / ts
    output_dir = Path(args.output_dir).expanduser() if args.output_dir else default_out

    if not base_config_path.exists():
        print(f"ERROR: base config not found: {base_config_path}")
        return 1

    base_cfg = load_config(base_config_path)
    posture = slack_base_posture(base_cfg)
    if args.check_base:
        out = dict(posture)
        out["mode"] = mode
        print(json.dumps(out, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        return 0

    try:
        result = generate_overlay_files(base_config_path, output_dir, mode, os.environ, created_utc=ts)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(result["overlay_config_path"])
        print(result["overlay_metadata_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

