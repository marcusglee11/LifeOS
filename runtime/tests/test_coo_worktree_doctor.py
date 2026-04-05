from __future__ import annotations

import json
import subprocess
from pathlib import Path

from runtime.tests.test_coo_worktree_breakglass import _prepare_repo, _run_start, _write_exec


def _run_doctor(
    repo_dir: Path, env: dict[str, str], *extra: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(repo_dir / "runtime" / "tools" / "coo_worktree.sh"), "doctor", *extra],
        cwd=repo_dir,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def _write_doctor_catalog(repo_dir: Path) -> None:
    catalog = {
        "version": 1,
        "reasons": {
            "gateway_probe_failed": {
                "severity": "hard",
                "drift_bypassable": False,
                "owner_system": "gateway",
                "remediation": {
                    "auto_fixable": True,
                    "action_id": "gateway.ensure",
                    "fix_command": "runtime/tools/openclaw_gateway_ensure.sh",
                    "manual_hint": "Gateway probe failed. Run coo doctor --apply-safe-fixes to attempt gateway restart, or run coo stop && coo start manually.",  # noqa: E501
                },
            },
            "model_ladder_policy_failed": {
                "severity": "drift",
                "drift_bypassable": True,
                "owner_system": "models",
                "remediation": {
                    "auto_fixable": True,
                    "action_id": "models.fix",
                    "fix_command": "coo models fix",
                    "manual_hint": None,
                },
            },
            "cron_delivery_guard_failed": {
                "severity": "drift",
                "drift_bypassable": True,
                "owner_system": "cron",
                "remediation": {
                    "auto_fixable": False,
                    "action_id": None,
                    "fix_command": None,
                    "manual_hint": "Cron delivery policy violation. Check openclaw cron list --all --json and set delivery.mode per policy.",  # noqa: E501
                },
            },
            "sandbox_mode_disallowed": {
                "severity": "hard",
                "drift_bypassable": False,
                "owner_system": "sandbox",
                "remediation": {
                    "auto_fixable": False,
                    "action_id": None,
                    "fix_command": None,
                    "manual_hint": "Adjust sandbox policy; contact the operator if the active posture is unexpected.",  # noqa: E501
                },
            },
        },
    }
    path = repo_dir / "config" / "openclaw" / "gate_reason_catalog.json"
    path.write_text(json.dumps(catalog, ensure_ascii=True) + "\n", encoding="utf-8")


def _install_gateway_capture_stub(repo_dir: Path) -> None:
    _write_exec(
        repo_dir / "runtime" / "tools" / "openclaw_gateway_ensure.sh",
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'if [ -n "${STUB_GATEWAY_ARGS_FILE:-}" ]; then',
                '  printf \'%s\\n\' "${*:-<none>}" >>"$STUB_GATEWAY_ARGS_FILE"',
                "fi",
                'exit "${STUB_GATEWAY_RC:-0}"',
            ]
        )
        + "\n",
    )


def test_doctor_healthy_exits_zero_no_blockers(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    _write_doctor_catalog(repo_dir)
    env["STUB_GATE_STATUS_JSON"] = json.dumps({"pass": True, "blocking_reasons": []})

    proc = _run_doctor(repo_dir, env)

    assert proc.returncode == 0, proc.stderr
    assert "DOCTOR_STATUS=ok" in proc.stdout


def test_doctor_gateway_probe_failed_emits_safe_fix_command(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    _write_doctor_catalog(repo_dir)
    env["STUB_VERIFY_RC"] = "1"
    env["STUB_GATE_STATUS_JSON"] = json.dumps(
        {"pass": False, "blocking_reasons": ["gateway_probe_failed"]}
    )

    proc = _run_doctor(repo_dir, env)

    assert proc.returncode == 1
    assert "BLOCKER_REASON=gateway_probe_failed" in proc.stdout
    assert "BLOCKER_SEVERITY=hard" in proc.stdout
    assert "BLOCKER_AUTO_FIXABLE=true" in proc.stdout
    assert "BLOCKER_FIX_COMMAND=runtime/tools/openclaw_gateway_ensure.sh" in proc.stdout


def test_doctor_model_ladder_policy_failed_emits_coo_models_fix(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    _write_doctor_catalog(repo_dir)
    env["STUB_VERIFY_RC"] = "1"
    env["STUB_GATE_STATUS_JSON"] = json.dumps(
        {"pass": False, "blocking_reasons": ["model_ladder_policy_failed"]}
    )

    proc = _run_doctor(repo_dir, env)

    assert proc.returncode == 1
    assert "BLOCKER_FIX_COMMAND=coo models fix" in proc.stdout


def test_doctor_cron_delivery_guard_failed_is_manual(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    _write_doctor_catalog(repo_dir)
    env["STUB_VERIFY_RC"] = "1"
    env["STUB_GATE_STATUS_JSON"] = json.dumps(
        {"pass": False, "blocking_reasons": ["cron_delivery_guard_failed"]}
    )

    proc = _run_doctor(repo_dir, env)

    assert proc.returncode == 1
    assert "BLOCKER_AUTO_FIXABLE=false" in proc.stdout
    assert "BLOCKER_MANUAL_HINT=Cron delivery policy violation." in proc.stdout
    assert "BLOCKER_FIX_COMMAND=" not in proc.stdout


def test_doctor_sandbox_hard_failure_is_manual(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    _write_doctor_catalog(repo_dir)
    env["STUB_VERIFY_RC"] = "1"
    env["STUB_GATE_STATUS_JSON"] = json.dumps(
        {"pass": False, "blocking_reasons": ["sandbox_mode_disallowed"]}
    )

    proc = _run_doctor(repo_dir, env)

    assert proc.returncode == 1
    assert "BLOCKER_SEVERITY=hard" in proc.stdout
    assert "BLOCKER_AUTO_FIXABLE=false" in proc.stdout


def test_doctor_mixed_hard_and_drift_classify_correctly(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    _write_doctor_catalog(repo_dir)
    env["STUB_VERIFY_RC"] = "1"
    env["STUB_GATE_STATUS_JSON"] = json.dumps(
        {
            "pass": False,
            "blocking_reasons": ["sandbox_mode_disallowed", "model_ladder_policy_failed"],
        }
    )

    proc = _run_doctor(repo_dir, env)

    assert proc.returncode == 1
    assert "BLOCKER_REASON=sandbox_mode_disallowed" in proc.stdout
    assert "BLOCKER_REASON=model_ladder_policy_failed" in proc.stdout
    assert "BLOCKER_SEVERITY=hard" in proc.stdout
    assert "BLOCKER_SEVERITY=drift" in proc.stdout


def test_doctor_apply_safe_fixes_calls_gateway_ensure(tmp_path: Path) -> None:
    repo_dir, env, state_dir = _prepare_repo(tmp_path)
    _write_doctor_catalog(repo_dir)
    _install_gateway_capture_stub(repo_dir)
    gateway_args = state_dir / "gateway_args.txt"
    env["STUB_GATEWAY_ARGS_FILE"] = str(gateway_args)
    env["STUB_VERIFY_RC"] = "1"
    env["STUB_GATE_STATUS_JSON"] = json.dumps(
        {"pass": False, "blocking_reasons": ["gateway_probe_failed"]}
    )

    proc = _run_doctor(repo_dir, env, "--apply-safe-fixes")

    assert proc.returncode == 1
    args_lines = gateway_args.read_text(encoding="utf-8").splitlines()
    assert "--check-only" in args_lines
    assert "<none>" in args_lines


def test_doctor_apply_safe_fixes_calls_coo_models_fix(tmp_path: Path) -> None:
    repo_dir, env, state_dir = _prepare_repo(tmp_path)
    _write_doctor_catalog(repo_dir)
    args_file = state_dir / "model_fix_args.txt"
    env["STUB_MODEL_FIX_ARGS_FILE"] = str(args_file)
    env["STUB_VERIFY_RC"] = "1"
    env["STUB_GATE_STATUS_JSON"] = json.dumps(
        {"pass": False, "blocking_reasons": ["model_ladder_policy_failed"]}
    )

    proc = _run_doctor(repo_dir, env, "--apply-safe-fixes")

    assert proc.returncode == 1
    args_value = args_file.read_text(encoding="utf-8")
    assert f"--config {env['OPENCLAW_CONFIG_PATH']}" in args_value


def test_doctor_apply_safe_fixes_does_not_touch_sandbox_failure(tmp_path: Path) -> None:
    repo_dir, env, state_dir = _prepare_repo(tmp_path)
    _write_doctor_catalog(repo_dir)
    _install_gateway_capture_stub(repo_dir)
    gateway_args = state_dir / "gateway_args.txt"
    env["STUB_GATEWAY_ARGS_FILE"] = str(gateway_args)
    args_file = state_dir / "model_fix_args.txt"
    env["STUB_MODEL_FIX_ARGS_FILE"] = str(args_file)
    env["STUB_VERIFY_RC"] = "1"
    env["STUB_GATE_STATUS_JSON"] = json.dumps(
        {"pass": False, "blocking_reasons": ["sandbox_mode_disallowed"]}
    )

    proc = _run_doctor(repo_dir, env, "--apply-safe-fixes")

    assert proc.returncode == 1
    args_lines = gateway_args.read_text(encoding="utf-8").splitlines()
    assert args_lines
    assert all(line == "--check-only" for line in args_lines)
    assert not args_file.exists()


def test_doctor_json_output_is_valid_json(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    _write_doctor_catalog(repo_dir)
    env["STUB_VERIFY_RC"] = "1"
    env["STUB_GATE_STATUS_JSON"] = json.dumps(
        {"pass": False, "blocking_reasons": ["gateway_probe_failed"]}
    )

    proc = _run_doctor(repo_dir, env, "--json")

    payload = json.loads(proc.stdout)
    assert payload["status"] == "blocked"
    assert "blockers" in payload
    assert "auto_fixes_applied" in payload


def test_doctor_json_healthy_status_is_ok(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    _write_doctor_catalog(repo_dir)
    env["STUB_GATE_STATUS_JSON"] = json.dumps({"pass": True, "blocking_reasons": []})

    proc = _run_doctor(repo_dir, env, "--json")

    payload = json.loads(proc.stdout)
    assert payload["status"] == "ok"


def test_doctor_json_blocked_has_blockers_list(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    _write_doctor_catalog(repo_dir)
    env["STUB_VERIFY_RC"] = "1"
    env["STUB_GATE_STATUS_JSON"] = json.dumps(
        {"pass": False, "blocking_reasons": ["model_ladder_policy_failed"]}
    )

    proc = _run_doctor(repo_dir, env, "--json")

    payload = json.loads(proc.stdout)
    assert payload["status"] == "blocked"
    assert payload["blockers"][0]["reason"] == "model_ladder_policy_failed"


def test_doctor_json_apply_safe_fixes_output_is_valid_json(tmp_path: Path) -> None:
    repo_dir, env, state_dir = _prepare_repo(tmp_path)
    _write_doctor_catalog(repo_dir)
    _install_gateway_capture_stub(repo_dir)
    env["STUB_GATEWAY_ARGS_FILE"] = str(state_dir / "gateway_args.txt")
    env["STUB_VERIFY_RC"] = "1"
    env["STUB_GATE_STATUS_JSON"] = json.dumps(
        {"pass": False, "blocking_reasons": ["gateway_probe_failed"]}
    )

    proc = _run_doctor(repo_dir, env, "--json", "--apply-safe-fixes")

    # stdout must be pure JSON — no subprocess noise from the fix scripts
    payload = json.loads(proc.stdout)
    assert payload["status"] in {"ok", "blocked"}
    assert "auto_fixes_applied" in payload


def test_doctor_without_gate_status_uses_probe_failure_reason(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    _write_doctor_catalog(repo_dir)
    _write_exec(
        repo_dir / "runtime" / "tools" / "openclaw_verify_surface.sh",
        "#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n",
    )
    env["STUB_GATEWAY_RC"] = "1"

    proc = _run_doctor(repo_dir, env)

    assert proc.returncode == 1
    assert "BLOCKER_REASON=startup_probe_failed" in proc.stdout


def test_start_failure_message_includes_coo_doctor(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    _write_doctor_catalog(repo_dir)
    env["STUB_VERIFY_RC"] = "1"
    env["STUB_GATE_STATUS_JSON"] = json.dumps(
        {"pass": False, "blocking_reasons": ["gateway_probe_failed"]}
    )

    proc = _run_start(repo_dir, env)

    assert proc.returncode == 1
    assert "coo doctor" in proc.stderr


def test_start_timeout_reports_timeout_message(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    _write_doctor_catalog(repo_dir)
    _write_exec(
        repo_dir / "runtime" / "tools" / "openclaw_gateway_ensure.sh",
        "#!/usr/bin/env bash\nset -euo pipefail\nsleep 2\n",
    )
    env["COO_STARTUP_TIMEOUT_SEC"] = "1"

    proc = _run_start(repo_dir, env)

    assert proc.returncode == 1
    assert "timed out" in proc.stderr
    assert "coo doctor" in proc.stderr
