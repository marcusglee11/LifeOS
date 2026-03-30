from __future__ import annotations

import json
from pathlib import Path

from runtime.tools.openclaw_sandbox_policy_assert import assert_sandbox_policy, extract_json_object


def _profile() -> dict[str, object]:
    return {
        "instance_id": "coo",
        "sandbox_policy": {
            "target_posture": "shared_ingress",
            "allowed_modes": ["all"],
            "require_session_sandboxed": True,
            "require_elevated_disabled": True,
        },
    }


def _payload(
    mode: str = "all", *, session_is_sandboxed: bool = True, elevated_enabled: bool = False
) -> dict[str, object]:
    return {
        "sandbox": {
            "mode": mode,
            "sessionIsSandboxed": session_is_sandboxed,
            "workspaceRoot": "/home/cabra/.openclaw/sandboxes",
        },
        "elevated": {
            "enabled": elevated_enabled,
        },
    }


def test_assert_sandbox_policy_passes_for_shared_ingress_all_mode() -> None:
    result = assert_sandbox_policy({}, _profile(), _payload())
    assert result["policy_ok"] is True
    assert result["violations"] == []
    assert result["observed_mode"] == "all"


def test_assert_sandbox_policy_rejects_disallowed_mode() -> None:
    result = assert_sandbox_policy({}, _profile(), _payload(mode="non-main"))
    assert result["policy_ok"] is False
    assert result["violations"] == ["sandbox_mode_disallowed"]


def test_assert_sandbox_policy_requires_sandboxed_session() -> None:
    result = assert_sandbox_policy({}, _profile(), _payload(session_is_sandboxed=False))
    assert result["policy_ok"] is False
    assert "sandbox_session_not_sandboxed" in result["violations"]


def test_assert_sandbox_policy_requires_elevated_disabled() -> None:
    result = assert_sandbox_policy({}, _profile(), _payload(elevated_enabled=True))
    assert result["policy_ok"] is False
    assert "sandbox_elevated_enabled" in result["violations"]


def test_extract_json_object_from_wrapped_capture_file(tmp_path: Path) -> None:
    payload = _payload()
    wrapped = (
        "```bash\ncoo openclaw -- sandbox explain --json\n```\n"
        "```text\n"
        f"{json.dumps(payload, indent=2)}\n"
        "[exit_code]=0\n"
        "```\n"
    )
    path = tmp_path / "sandbox.txt"
    path.write_text(wrapped, encoding="utf-8")

    result = extract_json_object(path.read_text(encoding="utf-8"))
    assert result["sandbox"]["mode"] == "all"
