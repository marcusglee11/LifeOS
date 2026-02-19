from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


def _write_exec(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _prepare_repo(tmp_path: Path) -> tuple[Path, dict[str, str], Path]:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    tools_dir = repo_dir / "runtime" / "tools"
    tools_dir.mkdir(parents=True)

    source_repo = Path(__file__).resolve().parents[2]
    coo_src = source_repo / "runtime" / "tools" / "coo_worktree.sh"
    coo_dst = tools_dir / "coo_worktree.sh"
    shutil.copy2(coo_src, coo_dst)
    coo_dst.chmod(coo_dst.stat().st_mode | stat.S_IEXEC)

    _write_exec(
        tools_dir / "openclaw_gateway_ensure.sh",
        "#!/usr/bin/env bash\nset -euo pipefail\nexit \"${STUB_GATEWAY_RC:-0}\"\n",
    )
    _write_exec(
        tools_dir / "openclaw_models_preflight.sh",
        "#!/usr/bin/env bash\nset -euo pipefail\nexit \"${STUB_PREFLIGHT_RC:-0}\"\n",
    )
    _write_exec(
        tools_dir / "openclaw_verify_surface.sh",
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "state_dir=\"${OPENCLAW_STATE_DIR:-$HOME/.openclaw}\"",
                "gate_status_path=\"${OPENCLAW_GATE_STATUS_PATH:-$state_dir/runtime/gates/gate_status.json}\"",
                "mkdir -p \"$(dirname \"$gate_status_path\")\"",
                "python3 - <<'PY' \"$gate_status_path\"",
                "import json",
                "import os",
                "import sys",
                "from pathlib import Path",
                "",
                "out = Path(sys.argv[1])",
                "raw = os.environ.get('STUB_GATE_STATUS_JSON', '')",
                "if raw:",
                "    obj = json.loads(raw)",
                "else:",
                "    obj = {'pass': True, 'blocking_reasons': []}",
                "out.write_text(json.dumps(obj, ensure_ascii=True) + '\\n', encoding='utf-8')",
                "PY",
                "echo \"PASS gate_status=$gate_status_path\"",
                "exit \"${STUB_VERIFY_RC:-0}\"",
            ]
        )
        + "\n",
    )

    _run(["git", "init"], repo_dir)
    _run(["git", "config", "user.email", "test@example.com"], repo_dir)
    _run(["git", "config", "user.name", "Test User"], repo_dir)
    (repo_dir / "README.md").write_text("test repo\n", encoding="utf-8")
    _run(["git", "add", "."], repo_dir)
    _run(["git", "commit", "-m", "init"], repo_dir)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_exec(
        bin_dir / "openclaw",
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "if [ \"${1:-}\" = \"dashboard\" ]; then",
                "  echo \"Dashboard URL: http://127.0.0.1:18789/#token=test-token\"",
                "  exit 0",
                "fi",
                "echo \"{}\"",
                "exit 0",
            ]
        )
        + "\n",
    )

    state_dir = tmp_path / "state"
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["OPENCLAW_STATE_DIR"] = str(state_dir)
    env["OPENCLAW_CONFIG_PATH"] = str(state_dir / "openclaw.json")
    env["STUB_GATEWAY_RC"] = "0"
    env["STUB_PREFLIGHT_RC"] = "0"
    return repo_dir, env, state_dir


def _run_start(repo_dir: Path, env: dict[str, str], *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(repo_dir / "runtime" / "tools" / "coo_worktree.sh"), "start", *extra],
        cwd=repo_dir,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def _gate_status(state_dir: Path) -> dict[str, object]:
    path = state_dir / "runtime" / "gates" / "gate_status.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_breakglass_allows_drift_only_failures(tmp_path: Path) -> None:
    repo_dir, env, state_dir = _prepare_repo(tmp_path)
    env["STUB_VERIFY_RC"] = "1"
    env["STUB_GATE_STATUS_JSON"] = json.dumps(
        {
            "pass": False,
            "blocking_reasons": [
                "policy_assert_failed",
                "model_ladder_policy_failed",
                "multiuser_posture_failed",
            ],
        }
    )

    proc = _run_start(repo_dir, env, "--unsafe-allow-drift")
    assert proc.returncode == 0, proc.stderr
    gate = _gate_status(state_dir)
    assert gate["break_glass_used"] is True
    assert gate["break_glass_scope"] == "policy_drift_only"
    assert gate["break_glass_bypass_reasons"] == [
        "policy_assert_failed",
        "model_ladder_policy_failed",
        "multiuser_posture_failed",
    ]


def test_breakglass_blocks_never_bypass_failures(tmp_path: Path) -> None:
    repo_dir, env, state_dir = _prepare_repo(tmp_path)
    env["STUB_VERIFY_RC"] = "1"
    env["STUB_GATE_STATUS_JSON"] = json.dumps(
        {
            "pass": False,
            "blocking_reasons": [
                "policy_assert_failed",
                "leak_scan_failed",
            ],
        }
    )

    proc = _run_start(repo_dir, env, "--unsafe-allow-drift")
    assert proc.returncode == 1
    gate = _gate_status(state_dir)
    assert gate["break_glass_used"] is True
    assert gate["break_glass_scope"] == "policy_drift_only"
    assert gate["break_glass_bypass_reasons"] == []


def test_start_without_failures_keeps_breakglass_off(tmp_path: Path) -> None:
    repo_dir, env, state_dir = _prepare_repo(tmp_path)
    env["STUB_VERIFY_RC"] = "0"
    env["STUB_GATE_STATUS_JSON"] = json.dumps({"pass": True, "blocking_reasons": []})

    proc = _run_start(repo_dir, env)
    assert proc.returncode == 0, proc.stderr
    gate = _gate_status(state_dir)
    assert gate["break_glass_used"] is False
    assert gate["break_glass_scope"] == "policy_drift_only"
    assert gate["break_glass_bypass_reasons"] == []


def test_start_resolves_repo_when_invoked_outside_repo(tmp_path: Path) -> None:
    """Script resolves repo root via BASH_SOURCE[0] even when cwd is outside any git repo."""
    repo_dir, env, state_dir = _prepare_repo(tmp_path)
    env["STUB_VERIFY_RC"] = "0"
    env["STUB_GATE_STATUS_JSON"] = json.dumps({"pass": True, "blocking_reasons": []})

    outside = tmp_path / "outside"
    outside.mkdir()
    proc = subprocess.run(
        [str(repo_dir / "runtime" / "tools" / "coo_worktree.sh"), "start"],
        cwd=outside,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    gate = _gate_status(state_dir)
    assert gate["break_glass_used"] is False
