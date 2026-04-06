"""Tests for runtime/tools/openclaw_instance_profile_lint.py"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from runtime.tools.openclaw_instance_profile_lint import lint_instance_profile


def _profile(**kwargs):
    base = {
        "instance_id": "coo",
        "sandbox_policy": {
            "target_posture": "unsandboxed",
            "allowed_modes": ["off"],
        },
    }
    base.update(kwargs)
    return base


class TestLintInstanceProfile:
    def test_valid_unsandboxed_profile(self):
        assert lint_instance_profile(_profile()) == []

    def test_missing_instance_id(self):
        p = _profile()
        p["instance_id"] = ""
        violations = lint_instance_profile(p)
        assert any("instance_id" in v for v in violations)

    def test_none_instance_id(self):
        p = _profile()
        p["instance_id"] = None
        violations = lint_instance_profile(p)
        assert any("instance_id" in v for v in violations)

    def test_unsandboxed_without_off_in_allowed_modes(self):
        p = _profile(sandbox_policy={"target_posture": "unsandboxed", "allowed_modes": ["all"]})
        violations = lint_instance_profile(p)
        assert any("'off'" in v for v in violations)

    def test_unsandboxed_with_only_all_in_allowed_modes(self):
        p = _profile(sandbox_policy={"target_posture": "unsandboxed", "allowed_modes": ["all"]})
        violations = lint_instance_profile(p)
        # Should flag both missing 'off' and the all-only case
        assert len(violations) >= 1

    def test_empty_allowed_modes(self):
        p = _profile(sandbox_policy={"target_posture": "unsandboxed", "allowed_modes": []})
        violations = lint_instance_profile(p)
        assert any("non-empty" in v for v in violations)

    def test_sandboxed_profile_all_allowed_ok(self):
        p = _profile(sandbox_policy={"target_posture": "shared_ingress", "allowed_modes": ["all"]})
        assert lint_instance_profile(p) == []

    def test_no_sandbox_policy_is_ok(self):
        p = {"instance_id": "coo"}
        assert lint_instance_profile(p) == []

    def test_reflects_current_clean_state(self):
        # Mirrors config/openclaw/instance_profiles/coo.json after today's fix
        p = {
            "instance_id": "coo",
            "profile_name": "coo_unsandboxed_prod_l3",
            "description": "Candidate: unsandboxed production with L3 autonomy ceiling",
            "run_user": "",
            "parity_jobs": [],
            "sandbox_policy": {
                "target_posture": "unsandboxed",
                "allowed_modes": ["off"],
                "require_session_sandboxed": False,
                "require_elevated_disabled": False,
            },
        }
        assert lint_instance_profile(p) == []
