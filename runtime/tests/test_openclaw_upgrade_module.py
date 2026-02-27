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
) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    _write_exec(bin_dir / "openclaw", openclaw_script)
    _write_exec(bin_dir / "npm", npm_script)
    _write_exec(bin_dir / "coo", coo_script)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
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
    assert payload["installed_version"] == "2026.2.23"
    assert payload["version_comparison"] == "behind"
    assert payload["update_available"] is True
    assert payload["health_gate"]["pass"] is False
    assert payload["needs_action"] is True
    assert payload["recommended_apply_command"] == "npm install -g openclaw@2026.2.25"


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
  echo "STATUS: VALID - all checks passed"
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


def test_registry_failure_fails_closed_with_json_payload(tmp_path: Path) -> None:
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
        args=["check"],
    )

    assert res.returncode == 2
    payload = json.loads(res.stdout)
    assert payload["registry_check"]["ok"] is False
    assert payload["registry_check"]["error"]
    assert payload["update_available"] is None
