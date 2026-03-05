from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)


def test_seq_allocate_is_monotonic(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    state_dir = tmp_path / "state"

    cmd = [
        "python3",
        "runtime/tools/openclaw_promotion_state.py",
        "--state-dir",
        str(state_dir),
        "seq-allocate",
        "--instance",
        "coo",
    ]
    first = _run(cmd, repo)
    second = _run(cmd, repo)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    first_obj = json.loads(first.stdout)
    second_obj = json.loads(second.stdout)
    assert int(second_obj["change_seq"]) == int(first_obj["change_seq"]) + 1


def test_apply_rejects_replay_ticket(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    state_dir = tmp_path / "state"
    packet_dir = tmp_path / "packet"
    packet_dir.mkdir(parents=True)

    now = int(time.time())
    packet = {
        "packet_id": "pkt-1",
        "ticket": {
            "ticket_id": "ticket-1",
            "change_seq": 7,
                "target_instance": "coo",
                "issued_at": now,
                "expires_at": now + 3600,
                "tip_at_issue": "tip123",
                "issuer": "coo",
                "signature": "UNSIGNED",
            },
    }
    (packet_dir / "promotion_packet.json").write_text(json.dumps(packet) + "\n", encoding="utf-8")

    attestation = tmp_path / "attestation.json"
    attestation.write_text(
        json.dumps(
            {
                "attestation_type": "preclose",
                "issued_unix": now,
                "expires_unix": now + 600,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    apply_cmd = [
        "python3",
        "runtime/tools/openclaw_promotion_state.py",
        "--state-dir",
        str(state_dir),
        "apply",
        "--packet-dir",
        str(packet_dir),
        "--attestation",
        str(attestation),
    ]

    first = _run(apply_cmd, repo)
    second = _run(apply_cmd, repo)

    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout)["pass"] is True

    assert second.returncode == 1
    second_payload = json.loads(second.stdout)
    assert second_payload["pass"] is False
    assert "promotion_replay_detected" in second_payload["errors"]
