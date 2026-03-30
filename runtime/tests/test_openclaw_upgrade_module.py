from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

SCRIPT = Path("runtime/tools/openclaw_upgrade_module.sh").resolve()


def _write_exec(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run_module(
    tmp_path: Path,
    *,
    openclaw_script: str,
    npm_script: str,
    coo_script: str,
    args: list[str],
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    _write_exec(bin_dir / "openclaw", openclaw_script)
    _write_exec(bin_dir / "npm", npm_script)
    _write_exec(bin_dir / "coo", coo_script)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [str(SCRIPT), *args],
        cwd=SCRIPT.parents[2],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_check_reports_update_available_and_invalid_health(tmp_path: Path) -> None:
    res = _run_module(
        tmp_path,
        openclaw_script="""#!/usr/bin/env bash
if [ "$1" = "--version" ]; then
  echo "2026.2.23"
  exit 0
fi
if [ "$1" = "update" ] && [ "${2:-}" = "status" ]; then
  echo '{"channel":{"value":"stable"}}'
  exit 0
fi
exit 1
""",
        npm_script="""#!/usr/bin/env bash
if [ "$1" = "view" ] && [ "$2" = "openclaw" ] && [ "$3" = "dist-tags" ] && [ "$4" = "--json" ]; then
  echo '{"latest":"2026.2.25","beta":"2026.2.25-beta.1"}'
  exit 0
fi
exit 1
""",
        coo_script="""#!/usr/bin/env bash
if [ "$1" = "models" ] && [ "$2" = "status" ]; then
  cat <<'OUT'
=== Model Ladder Health Status ===
STATUS: INVALID - 3 violation(s) detected
OUT
  exit 0
fi
exit 1
""",
        args=["check", "--channel", "stable"],
    )

    assert res.returncode == 0
    payload = json.loads(res.stdout)
    assert payload["registry_latest"] == "2026.2.25"
    assert payload["registry_source"] == "live"
    assert payload["installed_version"] == "2026.2.23"
    assert payload["version_comparison"] == "behind"
    assert payload["update_available"] is True
    assert payload["health_gate"]["pass"] is False
    assert payload["needs_action"] is True
    assert payload["recommended_apply_command"] == "npm install -g openclaw@2026.2.25"
    assert (
        payload["recommended_verify_command_template"]
        == "runtime/tools/openclaw_coo_update_protocol.sh promotion-verify --packet-dir <dir>"
    )
    assert (
        payload["recommended_record_command_template"]
        == "runtime/tools/openclaw_coo_update_protocol.sh promotion-run --packet-dir <dir>"
    )


def test_report_writes_status_file(tmp_path: Path) -> None:
    out_path = tmp_path / "status" / "openclaw_upgrade_status.json"
    res = _run_module(
        tmp_path,
        openclaw_script="""#!/usr/bin/env bash
if [ "$1" = "--version" ]; then
  echo "2026.2.25"
  exit 0
fi
if [ "$1" = "update" ] && [ "${2:-}" = "status" ]; then
  echo '{"channel":{"value":"stable"}}'
  exit 0
fi
exit 1
""",
        npm_script="""#!/usr/bin/env bash
echo '{"latest":"2026.2.25","beta":"2026.2.25-beta.1"}'
exit 0
""",
        coo_script="""#!/usr/bin/env bash
if [ "$1" = "models" ] && [ "$2" = "status" ]; then
  echo "STATUS: OK - all ladders satisfy policy"
  exit 0
fi
exit 1
""",
        args=["report", "--out", str(out_path)],
    )

    assert res.returncode == 0
    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["status_report_path"] == str(out_path)
    assert payload["update_available"] is False
    assert payload["needs_action"] is False
    assert payload["health_gate"]["pass"] is True
    assert payload["health_gate"]["reason"] == "ok"


def test_registry_retry_succeeds_after_transient_failure(tmp_path: Path) -> None:
    res = _run_module(
        tmp_path,
        openclaw_script="""#!/usr/bin/env bash
if [ "$1" = "--version" ]; then
  echo "2026.2.24"
  exit 0
fi
exit 1
""",
        npm_script="""#!/usr/bin/env bash
STATE_FILE="$(dirname "$0")/.npm_calls"
COUNT=0
if [ -f "$STATE_FILE" ]; then
  COUNT="$(cat "$STATE_FILE")"
fi
COUNT="$((COUNT + 1))"
echo "$COUNT" > "$STATE_FILE"
if [ "$COUNT" -lt 2 ]; then
  echo "fetch failed" >&2
  exit 1
fi
echo '{"latest":"2026.2.25","beta":"2026.2.25-beta.1"}'
exit 0
""",
        coo_script="""#!/usr/bin/env bash
echo "STATUS: OK - all ladders satisfy policy"
exit 0
""",
        args=["check"],
        extra_env={
            "OPENCLAW_UPGRADE_NPM_RETRIES": "2",
            "OPENCLAW_UPGRADE_NPM_RETRY_DELAY_SEC": "0",
        },
    )

    assert res.returncode == 0
    payload = json.loads(res.stdout)
    assert payload["registry_check"]["ok"] is True
    assert payload["registry_check"]["attempts"] == 2
    assert payload["registry_source"] == "live"
    assert payload["registry_latest"] == "2026.2.25"


def test_registry_cache_fallback_used_after_live_failures(tmp_path: Path) -> None:
    out_path = tmp_path / "status" / "openclaw_upgrade_status.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"registry_dist_tags": {"latest": "2026.2.25"}}, indent=2) + "\n",
        encoding="utf-8",
    )

    res = _run_module(
        tmp_path,
        openclaw_script="""#!/usr/bin/env bash
if [ "$1" = "--version" ]; then
  echo "2026.2.24"
  exit 0
fi
exit 1
""",
        npm_script="""#!/usr/bin/env bash
echo "fetch failed" >&2
exit 1
""",
        coo_script="""#!/usr/bin/env bash
echo "STATUS: OK - all ladders satisfy policy"
exit 0
""",
        args=["check", "--out", str(out_path)],
        extra_env={
            "OPENCLAW_UPGRADE_NPM_RETRIES": "2",
            "OPENCLAW_UPGRADE_NPM_RETRY_DELAY_SEC": "0",
        },
    )

    assert res.returncode == 0
    payload = json.loads(res.stdout)
    assert payload["registry_check"]["ok"] is True
    assert payload["registry_source"] == "cache"
    assert payload["registry_latest"] == "2026.2.25"
    assert "warning" in payload["registry_check"]


def test_registry_failure_fails_closed_with_json_payload(tmp_path: Path) -> None:
    out_path = tmp_path / "status" / "empty_cache.json"
    res = _run_module(
        tmp_path,
        openclaw_script="""#!/usr/bin/env bash
if [ "$1" = "--version" ]; then
  echo "2026.2.23"
  exit 0
fi
exit 1
""",
        npm_script="""#!/usr/bin/env bash
echo "fetch failed" >&2
exit 1
""",
        coo_script="""#!/usr/bin/env bash
echo "STATUS: VALID - all checks passed"
exit 0
""",
        args=["check", "--out", str(out_path)],
        extra_env={
            "OPENCLAW_UPGRADE_NPM_RETRIES": "2",
            "OPENCLAW_UPGRADE_NPM_RETRY_DELAY_SEC": "0",
        },
    )

    assert res.returncode == 2
    payload = json.loads(res.stdout)
    assert payload["registry_check"]["ok"] is False
    assert payload["registry_check"]["error"]
    assert payload["registry_source"] == "none"
    assert payload["update_available"] is None


def test_propose_returns_install_then_record_sequence(tmp_path: Path) -> None:
    res = _run_module(
        tmp_path,
        openclaw_script="""#!/usr/bin/env bash
if [ "$1" = "--version" ]; then
  echo "2026.2.23"
  exit 0
fi
if [ "$1" = "update" ] && [ "${2:-}" = "status" ]; then
  echo '{"channel":{"value":"stable"}}'
  exit 0
fi
exit 1
""",
        npm_script="""#!/usr/bin/env bash
if [ "$1" = "view" ] && [ "$2" = "openclaw" ] && [ "$3" = "dist-tags" ] && [ "$4" = "--json" ]; then
  echo '{"latest":"2026.2.25","beta":"2026.2.25-beta.1"}'
  exit 0
fi
exit 1
""",
        coo_script="""#!/usr/bin/env bash
if [ "$1" = "models" ] && [ "$2" = "status" ]; then
  echo "STATUS: OK - all ladders satisfy policy"
  exit 0
fi
exit 1
""",
        args=["propose", "--channel", "stable"],
    )

    assert res.returncode == 0
    payload = json.loads(res.stdout)
    assert payload["recommended_apply_command"] == "npm install -g openclaw@2026.2.25"
    base = payload["promotion_packet_base"]
    assert base["target_version"] == "2026.2.25"
    assert base["previous_version"] == "2026.2.23"
    assert base["target_commit"]  # non-empty HEAD sha
    assert payload["proposal"]["mode"] == "manual_apply_then_record"
    assert payload["proposal"]["apply_then_record"] == [
        "npm install -g openclaw@2026.2.25",
        "openclaw --version",
        "runtime/tools/openclaw_coo_update_protocol.sh promotion-verify --packet-dir <dir>",
        "runtime/tools/openclaw_coo_update_protocol.sh promotion-run --packet-dir <dir>",
    ]
