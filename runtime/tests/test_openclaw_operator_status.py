from __future__ import annotations

import json

from runtime.tools.openclaw_operator_status import (
    _parse_mig_candidates,
    _pick_running_instance,
    classify_auth_health,
)


def test_parse_mig_candidates_prefers_named_and_openclaw() -> None:
    raw = json.dumps(
        [
            {
                "name": "misc-mig",
                "zone": "https://www.googleapis.com/compute/v1/projects/p/zones/us-central1-a",
                "targetSize": 1,
            },
            {
                "name": "openclaw-main-mig",
                "zone": "https://www.googleapis.com/compute/v1/projects/p/zones/us-central1-b",
                "targetSize": 1,
            },
        ]
    )
    items = _parse_mig_candidates(raw, preferred_name="openclaw-main-mig")
    assert items
    assert items[0].name == "openclaw-main-mig"
    assert items[0].location == "us-central1-b"
    assert items[0].scope == "zone"


def test_pick_running_instance_prefers_running_none_action() -> None:
    raw = json.dumps(
        [
            {
                "instance": "https://www.googleapis.com/compute/v1/projects/p/zones/us-central1-a/instances/openclaw-001",
                "instanceStatus": "RUNNING",
                "currentAction": "NONE",
            },
            {
                "instance": "https://www.googleapis.com/compute/v1/projects/p/zones/us-central1-a/instances/openclaw-002",
                "instanceStatus": "STAGING",
                "currentAction": "CREATING",
            },
        ]
    )
    name, zone = _pick_running_instance(raw, fallback_zone="us-central1-a")
    assert name == "openclaw-001"
    assert zone == "us-central1-a"


def test_classify_auth_health_ok() -> None:
    result = classify_auth_health(0, "models status check passed")
    assert result["state"] == "ok"
    assert result["reason_code"] == "ok"


def test_classify_auth_health_cooldown() -> None:
    result = classify_auth_health(1, "provider openai-codex is in cooldown")
    assert result["state"] == "cooldown"
    assert result["reason_code"] == "provider_cooldown"
    assert result["provider"] == "openai-codex"


def test_classify_auth_health_invalid_missing() -> None:
    result = classify_auth_health(1, "authentication required: token has been invalidated")
    assert result["state"] == "invalid_missing"
    assert result["reason_code"] == "expired_or_missing"
