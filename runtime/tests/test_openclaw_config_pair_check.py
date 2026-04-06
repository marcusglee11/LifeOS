"""Tests for runtime/tools/openclaw_config_pair_check.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from runtime.tools.openclaw_config_pair_check import check_config_pair, _resolve_sandbox_mode, _has_docker_config


def _config(defaults_mode=None, main_mode=None, main_docker=None):
    agents: dict = {}
    if defaults_mode is not None:
        agents["defaults"] = {"sandbox": {"mode": defaults_mode}}
    if main_mode is not None or main_docker is not None:
        sb: dict = {}
        if main_mode is not None:
            sb["mode"] = main_mode
        if main_docker is not None:
            sb["docker"] = main_docker
        agents["list"] = [{"id": "main", "sandbox": sb}]
    return {"agents": agents}


def _profile(allowed_modes=None, target_posture="unsandboxed"):
    return {
        "instance_id": "coo",
        "sandbox_policy": {
            "target_posture": target_posture,
            "allowed_modes": allowed_modes or ["off"],
        },
    }


class TestResolveSandboxMode:
    def test_defaults_only(self):
        assert _resolve_sandbox_mode(_config(defaults_mode="off")) == "off"

    def test_main_agent_overrides_defaults(self):
        cfg = _config(defaults_mode="all", main_mode="off")
        assert _resolve_sandbox_mode(cfg) == "off"

    def test_no_config_returns_off(self):
        assert _resolve_sandbox_mode({}) == "off"

    def test_list_as_dict(self):
        cfg = {"agents": {"list": {"main": {"sandbox": {"mode": "non-main"}}}}}
        assert _resolve_sandbox_mode(cfg) == "non-main"


class TestHasDockerConfig:
    def test_no_docker(self):
        assert _has_docker_config(_config(main_mode="off")) is False

    def test_main_agent_docker(self):
        cfg = _config(main_mode="off", main_docker={"binds": ["/foo:/bar:ro"]})
        assert _has_docker_config(cfg) is True

    def test_defaults_docker(self):
        cfg = {"agents": {"defaults": {"sandbox": {"mode": "off", "docker": {"binds": []}}}}}
        assert _has_docker_config(cfg) is True


class TestCheckConfigPair:
    def test_clean_off_mode_matching_profile(self):
        result = check_config_pair(_config(main_mode="off"), _profile(["off"]))
        assert result["pair_check_ok"] is True
        assert result["violations"] == []

    def test_sandbox_mode_disallowed(self):
        # mode=off but profile only allows "all"
        result = check_config_pair(_config(main_mode="off"), _profile(["all"]))
        assert result["pair_check_ok"] is False
        assert "sandbox_mode_disallowed" in result["violations"]

    def test_docker_dead_config(self):
        cfg = _config(main_mode="off", main_docker={"binds": ["/lifeos:/lifeos:ro"]})
        result = check_config_pair(cfg, _profile(["off"]))
        assert result["pair_check_ok"] is False
        assert "docker_dead_config" in result["violations"]

    def test_docker_allowed_when_sandbox_on(self):
        cfg = _config(main_mode="all", main_docker={"binds": ["/foo:/foo:ro"]})
        result = check_config_pair(cfg, _profile(["all"]))
        assert result["pair_check_ok"] is True
        assert result["docker_dead_config"] is False

    def test_both_violations(self):
        # mode=off, profile requires "all", AND docker dead config
        cfg = _config(main_mode="off", main_docker={"binds": ["/x:/x"]})
        result = check_config_pair(cfg, _profile(["all"]))
        assert result["pair_check_ok"] is False
        assert "sandbox_mode_disallowed" in result["violations"]
        assert "docker_dead_config" in result["violations"]

    def test_empty_allowed_modes_treated_as_no_constraint(self):
        result = check_config_pair(_config(main_mode="off"), _profile([]))
        # Empty allowed_modes → no constraint enforced
        assert result["sandbox_mode_allowed"] is True

    def test_reflects_today_clean_state(self):
        # Mirrors the state after today's fixes: mode=off, allowed_modes=["off"], no docker
        result = check_config_pair(_config(main_mode="off"), _profile(["off"]))
        assert result["pair_check_ok"] is True
        assert result["sandbox_mode"] == "off"
        assert result["allowed_modes"] == ["off"]
