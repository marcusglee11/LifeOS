from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

from runtime.tools import openclaw_distill_lane as lane


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
    catalog_dir = repo_dir / "config" / "openclaw"
    catalog_dir.mkdir(parents=True)

    source_repo = Path(__file__).resolve().parents[2]
    coo_src = source_repo / "runtime" / "tools" / "coo_worktree.sh"
    coo_dst = tools_dir / "coo_worktree.sh"
    shutil.copy2(coo_src, coo_dst)
    coo_dst.chmod(coo_dst.stat().st_mode | stat.S_IEXEC)
    shutil.copy2(
        source_repo / "runtime" / "tools" / "openclaw_distill_lane.py",
        tools_dir / "openclaw_distill_lane.py",
    )

    _write_exec(
        tools_dir / "openclaw_gateway_ensure.sh",
        '#!/usr/bin/env bash\nset -euo pipefail\nexit "${STUB_GATEWAY_RC:-0}"\n',
    )
    _write_exec(
        tools_dir / "openclaw_models_preflight.sh",
        '#!/usr/bin/env bash\nset -euo pipefail\nexit "${STUB_PREFLIGHT_RC:-0}"\n',
    )
    _write_exec(
        tools_dir / "openclaw_verify_surface.sh",
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'state_dir="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"',
                'gate_status_path="${OPENCLAW_GATE_STATUS_PATH:-$state_dir/runtime/gates/gate_status.json}"',
                'mkdir -p "$(dirname "$gate_status_path")"',
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
                'echo "PASS gate_status=$gate_status_path"',
                'exit "${STUB_VERIFY_RC:-0}"',
            ]
        )
        + "\n",
    )
    _write_exec(
        tools_dir / "openclaw_model_policy_assert.py",
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import os",
                "import sys",
                "",
                'print(os.environ.get(\'STUB_MODEL_POLICY_JSON\', \'{"policy_ok":true,"violations":[],"ladders":{}}\'))',
                "raise SystemExit(int(os.environ.get('STUB_MODEL_POLICY_RC', '0')))",
            ]
        )
        + "\n",
    )
    _write_exec(
        tools_dir / "openclaw_model_ladder_fix.py",
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import os",
                "import sys",
                "",
                "out = os.environ.get('STUB_MODEL_FIX_ARGS_FILE')",
                "if out:",
                "    with open(out, 'w', encoding='utf-8') as f:",
                "        f.write(' '.join(sys.argv[1:]))",
                "raise SystemExit(int(os.environ.get('STUB_MODEL_FIX_RC', '0')))",
            ]
        )
        + "\n",
    )
    (catalog_dir / "gate_reason_catalog.json").write_text(
        json.dumps(
            {
                "version": 1,
                "reasons": {
                    "policy_assert_failed": {"severity": "drift", "drift_bypassable": True},
                    "model_ladder_policy_failed": {"severity": "drift", "drift_bypassable": True},
                    "multiuser_posture_failed": {"severity": "drift", "drift_bypassable": True},
                    "interfaces_policy_failed": {"severity": "drift", "drift_bypassable": True},
                    "cron_delivery_guard_failed": {"severity": "drift", "drift_bypassable": True},
                    "sandbox_mode_disallowed": {"severity": "hard", "drift_bypassable": False},
                    "sandbox_session_not_sandboxed": {
                        "severity": "hard",
                        "drift_bypassable": False,
                    },
                    "sandbox_explain_parse_failed": {"severity": "hard", "drift_bypassable": False},
                    "sandbox_elevated_enabled": {"severity": "hard", "drift_bypassable": False},
                    "leak_scan_failed": {"severity": "hard", "drift_bypassable": False},
                    "gate_reason_unknown": {"severity": "hard", "drift_bypassable": False},
                    "gate_reason_catalog_failed": {"severity": "hard", "drift_bypassable": False},
                },
            },
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
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
                'if [ "${1:-}" = "agent" ] && [ "${2:-}" = "--local" ] && [ "${3:-}" = "--agent" ] && [ "${4:-}" = "quick" ]; then',
                '  if [ "${STUB_QUICK_FAIL:-0}" = "1" ]; then',
                "    echo 'quick unavailable' >&2",
                "    exit 1",
                "  fi",
                '  if [ "${9:-}" = "Reply READY" ]; then',
                '    echo \'{"payloads":[{"text":"READY"}]}\'',
                "    exit 0",
                "  fi",
                '  if [ -n "${STUB_DISTILL_JSON:-}" ]; then',
                '    echo "${STUB_DISTILL_JSON}"',
                "  else",
                '    echo \'{"payloads":[{"text":"{\\"status\\":\\"ok\\",\\"template_id\\":\\"actionable_faults\\",\\"summary\\":[\\"fallback\\"],\\"key_entities\\":[\\"openclaw\\"],\\"raw_payload_sha256\\":\\"missing\\",\\"traffic_class\\":\\"repo_scans\\",\\"source_command\\":\\"openclaw models status\\",\\"bypass_reason\\":null}"}]}\'',
                "  fi",
                "  exit 0",
                "fi",
                'if [ "${1:-}" = "--version" ]; then',
                '  echo "${STUB_OPENCLAW_VERSION:-openclaw 1.2.3}"',
                "  exit 0",
                "fi",
                'if [ "${1:-}" = "models" ] && [ "${2:-}" = "status" ]; then',
                "  printf '%s' \"${STUB_MODELS_STATUS:-openai-codex/gpt-5.3-codex text yes configured}\"",
                "  exit 0",
                "fi",
                'if [ "${1:-}" = "status" ] && [ "${2:-}" = "--usage" ]; then',
                "  printf '%s' \"${STUB_STATUS_USAGE:-openai usage visible}\"",
                "  exit 0",
                "fi",
                'if [ "${1:-}" = "status" ] && [ "${2:-}" = "--all" ] && [ "${3:-}" = "--usage" ]; then',
                "  printf '%s' \"${STUB_STATUS_ALL_USAGE:-- openai-codex usage: 90% left}\"",
                "  exit 0",
                "fi",
                'if [ "${1:-}" = "dashboard" ]; then',
                '  echo "Dashboard URL: http://127.0.0.1:18789/#token=test-token"',
                "  exit 0",
                "fi",
                'echo "{}"',
                "exit 0",
            ]
        )
        + "\n",
    )

    state_dir = tmp_path / "state"
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["OPENCLAW_BIN"] = str(bin_dir / "openclaw")
    env["OPENCLAW_STATE_DIR"] = str(state_dir)
    env["OPENCLAW_CONFIG_PATH"] = str(state_dir / "openclaw.json")
    env["STUB_GATEWAY_RC"] = "0"
    env["STUB_PREFLIGHT_RC"] = "0"
    return repo_dir, env, state_dir


def _write_active_health_receipt(state_dir: Path, env: dict[str, str]) -> None:
    context = lane.build_runtime_context(
        openclaw_bin=env["OPENCLAW_BIN"],
        profile="",
        env=env,
    )
    fingerprint, _payload = lane.build_compatibility_fingerprint(context)
    lane.health_path_for_state(state_dir).parent.mkdir(parents=True, exist_ok=True)
    lane.health_path_for_state(state_dir).write_text(
        json.dumps(
            {
                "effective_mode": "active",
                "compatibility_fingerprint": fingerprint,
                "last_successful_preflight_fingerprint": fingerprint,
                "preflight_ok": True,
                "last_preflight_ts_utc": lane._utc_now(),  # noqa: SLF001
            }
        ),
        encoding="utf-8",
    )
    lane.shadow_success_receipt_path_for_state(state_dir).write_text(
        json.dumps(
            {
                "compatibility_fingerprint": fingerprint,
                "ceo_approved": True,
            }
        ),
        encoding="utf-8",
    )
    lane.forced_failure_receipt_path_for_state(state_dir).write_text(
        json.dumps(
            {
                "compatibility_fingerprint": fingerprint,
                "drill_passed": True,
            }
        ),
        encoding="utf-8",
    )


def _run_start(
    repo_dir: Path, env: dict[str, str], *extra: str
) -> subprocess.CompletedProcess[str]:
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


def test_breakglass_blocks_sandbox_policy_failures(tmp_path: Path) -> None:
    repo_dir, env, state_dir = _prepare_repo(tmp_path)
    env["STUB_VERIFY_RC"] = "1"
    env["STUB_GATE_STATUS_JSON"] = json.dumps(
        {
            "pass": False,
            "blocking_reasons": [
                "sandbox_mode_disallowed",
            ],
        }
    )

    proc = _run_start(repo_dir, env, "--unsafe-allow-drift")
    assert proc.returncode == 1
    gate = _gate_status(state_dir)
    assert gate["break_glass_used"] is True
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


def test_models_status_parses_policy_json(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    env["STUB_MODEL_POLICY_RC"] = "1"
    env["STUB_MODEL_POLICY_JSON"] = json.dumps(
        {
            "policy_ok": False,
            "violations": ["main: no working model detected in configured ladder"],
            "ladders": {
                "main": {
                    "actual": ["openai-codex/gpt-5.3-codex", "openai-codex/gpt-5.1"],
                    "required_prefix": [
                        "openai-codex/gpt-5.3-codex",
                        "openai-codex/gpt-5.1",
                        "openai-codex/gpt-5.1-codex-max",
                    ],
                    "working_count": 0,
                    "top_rung_auth_missing": True,
                }
            },
        }
    )

    proc = subprocess.run(
        [str(repo_dir / "runtime" / "tools" / "coo_worktree.sh"), "models", "status"],
        cwd=repo_dir,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert "STATUS: INVALID - 1 violation(s) detected" in proc.stdout
    assert "WARNING: Top rung (openai-codex/gpt-5.3-codex) not authenticated" in proc.stdout


def test_openclaw_models_status_distill_shadow_preserves_raw_output_and_writes_audit(
    tmp_path: Path,
) -> None:
    repo_dir, env, state_dir = _prepare_repo(tmp_path)
    env["LIFEOS_DISTILL_ENABLE"] = "1"
    env["LIFEOS_DISTILL_MODE"] = "shadow"
    raw = "openai-codex/gpt-5.3-codex text yes configured\n" + ("X" * 9000)
    env["STUB_MODELS_STATUS"] = raw
    raw_hash = __import__("hashlib").sha256(raw.encode("utf-8")).hexdigest()
    distill_payload = {
        "payloads": [
            {
                "text": json.dumps(
                    {
                        "status": "ok",
                        "template_id": "actionable_faults",
                        "summary": ["auth healthy"],
                        "key_entities": ["openai-codex"],
                        "raw_payload_sha256": raw_hash,
                        "traffic_class": "repo_scans",
                        "source_command": "models status",
                        "bypass_reason": None,
                    }
                )
            }
        ]
    }
    env["STUB_DISTILL_JSON"] = json.dumps(distill_payload)

    proc = subprocess.run(
        [
            str(repo_dir / "runtime" / "tools" / "coo_worktree.sh"),
            "openclaw",
            "--",
            "models",
            "status",
        ],
        cwd=repo_dir,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "openai-codex/gpt-5.3-codex" in proc.stdout
    audit_path = state_dir / "runtime" / "gates" / "distill" / "audit.jsonl"
    assert audit_path.exists()
    assert "repo_scans" in audit_path.read_text(encoding="utf-8")


def test_openclaw_sandbox_explain_does_not_require_training_worktree(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)

    proc = subprocess.run(
        [
            str(repo_dir / "runtime" / "tools" / "coo_worktree.sh"),
            "openclaw",
            "--",
            "sandbox",
            "explain",
            "--json",
        ],
        cwd=repo_dir,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert "{}" in proc.stdout


def test_openclaw_models_status_distill_active_replaces_output(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    _write_active_health_receipt(Path(env["OPENCLAW_STATE_DIR"]), env)
    env["LIFEOS_DISTILL_ENABLE"] = "1"
    env["LIFEOS_DISTILL_MODE"] = "active"
    raw = "openai-codex/gpt-5.3-codex text yes configured\n" + ("Y" * 9000)
    env["STUB_MODELS_STATUS"] = raw
    raw_hash = __import__("hashlib").sha256(raw.encode("utf-8")).hexdigest()
    distill_payload = {
        "payloads": [
            {
                "text": json.dumps(
                    {
                        "status": "ok",
                        "template_id": "actionable_faults",
                        "summary": ["auth healthy"],
                        "key_entities": ["openai-codex"],
                        "raw_payload_sha256": raw_hash,
                        "traffic_class": "repo_scans",
                        "source_command": "models status",
                        "bypass_reason": None,
                    }
                )
            }
        ]
    }
    env["STUB_DISTILL_JSON"] = json.dumps(distill_payload)

    proc = subprocess.run(
        [
            str(repo_dir / "runtime" / "tools" / "coo_worktree.sh"),
            "openclaw",
            "--",
            "models",
            "status",
        ],
        cwd=repo_dir,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "DISTILL_STATUS=ok" in proc.stdout
    assert "SUMMARY_BEGIN" in proc.stdout
    assert "openai-codex/gpt-5.3-codex text yes configured" not in proc.stdout


def test_openclaw_status_all_usage_active_never_replaces_output(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    _write_active_health_receipt(Path(env["OPENCLAW_STATE_DIR"]), env)
    env["LIFEOS_DISTILL_ENABLE"] = "1"
    env["LIFEOS_DISTILL_MODE"] = "active"
    raw = "- openai-codex usage: 90% left\n" + ("Z" * 9000)
    env["STUB_STATUS_ALL_USAGE"] = raw
    raw_hash = __import__("hashlib").sha256(raw.encode("utf-8")).hexdigest()
    distill_payload = {
        "payloads": [
            {
                "text": json.dumps(
                    {
                        "status": "ok",
                        "template_id": "actionable_faults",
                        "summary": ["budget healthy"],
                        "key_entities": ["openai-codex"],
                        "raw_payload_sha256": raw_hash,
                        "traffic_class": "repo_scans",
                        "source_command": "status --all --usage",
                        "bypass_reason": None,
                    }
                )
            }
        ]
    }
    env["STUB_DISTILL_JSON"] = json.dumps(distill_payload)

    proc = subprocess.run(
        [
            str(repo_dir / "runtime" / "tools" / "coo_worktree.sh"),
            "openclaw",
            "--",
            "status",
            "--all",
            "--usage",
        ],
        cwd=repo_dir,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "- openai-codex usage: 90% left" in proc.stdout
    assert "DISTILL_STATUS=ok" not in proc.stdout


def test_openclaw_models_status_active_without_health_receipt_bypasses_to_raw(
    tmp_path: Path,
) -> None:
    repo_dir, env, state_dir = _prepare_repo(tmp_path)
    env["LIFEOS_DISTILL_ENABLE"] = "1"
    env["LIFEOS_DISTILL_MODE"] = "active"
    raw = "openai-codex/gpt-5.3-codex text yes configured\n" + ("Q" * 9000)
    env["STUB_MODELS_STATUS"] = raw

    proc = subprocess.run(
        [
            str(repo_dir / "runtime" / "tools" / "coo_worktree.sh"),
            "openclaw",
            "--",
            "models",
            "status",
        ],
        cwd=repo_dir,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "openai-codex/gpt-5.3-codex text yes configured" in proc.stdout
    audit_entries = [
        json.loads(line)
        for line in (state_dir / "runtime" / "gates" / "distill" / "audit.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    attempts = [entry for entry in audit_entries if entry.get("event_type") == "attempt"]
    assert attempts[-1]["bypass_reason"] == "health_state_invalid"


def test_models_fix_uses_openclaw_config_path(tmp_path: Path) -> None:
    repo_dir, env, state_dir = _prepare_repo(tmp_path)
    args_file = state_dir / "model_fix_args.txt"
    env["STUB_MODEL_FIX_ARGS_FILE"] = str(args_file)

    proc = subprocess.run(
        [str(repo_dir / "runtime" / "tools" / "coo_worktree.sh"), "models", "fix"],
        cwd=repo_dir,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    args_value = args_file.read_text(encoding="utf-8")
    assert f"--config {env['OPENCLAW_CONFIG_PATH']}" in args_value
