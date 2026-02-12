import json
import os
import subprocess
import sys
from pathlib import Path

from runtime.tools.openclaw_slack_overlay import generate_overlay_files, slack_base_posture


def _base_cfg() -> dict:
    return {
        "channels": {
            "slack": {
                "enabled": False,
                "mode": "socket",
            }
        }
    }


def _write_cfg(path: Path, cfg: dict) -> None:
    path.write_text(json.dumps(cfg), encoding="utf-8")


def test_socket_mode_missing_env_fails(tmp_path: Path):
    cfg_path = tmp_path / "openclaw.json"
    _write_cfg(cfg_path, _base_cfg())
    try:
        generate_overlay_files(cfg_path, tmp_path / "out", "socket", {})
    except ValueError as exc:
        assert "missing required env" in str(exc)
    else:
        raise AssertionError("expected missing env failure")


def test_http_mode_missing_signing_secret_fails(tmp_path: Path):
    cfg_path = tmp_path / "openclaw.json"
    _write_cfg(cfg_path, _base_cfg())
    env = {"OPENCLAW_SLACK_BOT_TOKEN": "xoxb-TEST-DUMMY"}
    try:
        generate_overlay_files(cfg_path, tmp_path / "out", "http", env)
    except ValueError as exc:
        assert "missing required env" in str(exc)
    else:
        raise AssertionError("expected missing signing secret failure")


def test_socket_dummy_env_generates_overlay_metadata_without_secrets(tmp_path: Path):
    cfg_path = tmp_path / "openclaw.json"
    _write_cfg(cfg_path, _base_cfg())
    env = {
        "OPENCLAW_SLACK_APP_TOKEN": "xapp-TEST-DUMMY-TOKEN",
        "OPENCLAW_SLACK_BOT_TOKEN": "xoxb-TEST-DUMMY-TOKEN",
    }
    result = generate_overlay_files(cfg_path, tmp_path / "out", "socket", env)
    meta = Path(result["overlay_metadata_path"]).read_text(encoding="utf-8")
    assert '"OPENCLAW_SLACK_APP_TOKEN":true' in meta
    assert '"OPENCLAW_SLACK_BOT_TOKEN":true' in meta
    assert "xapp-TEST-DUMMY-TOKEN" not in meta
    assert "xoxb-TEST-DUMMY-TOKEN" not in meta


def test_cli_output_never_logs_token_values(tmp_path: Path):
    cfg_path = tmp_path / "openclaw.json"
    _write_cfg(cfg_path, _base_cfg())
    out_dir = tmp_path / "out"
    env = os.environ.copy()
    env.update(
        {
            "OPENCLAW_CONFIG_PATH": str(cfg_path),
            "OPENCLAW_SLACK_APP_TOKEN": "xapp-TEST-DUMMY-TOKEN",
            "OPENCLAW_SLACK_BOT_TOKEN": "xoxb-TEST-DUMMY-TOKEN",
        }
    )
    proc = subprocess.run(
        [
            sys.executable,
            "runtime/tools/openclaw_slack_overlay.py",
            "--mode",
            "socket",
            "--output-dir",
            str(out_dir),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    joined = proc.stdout + proc.stderr
    assert "xapp-TEST-DUMMY-TOKEN" not in joined
    assert "xoxb-TEST-DUMMY-TOKEN" not in joined

