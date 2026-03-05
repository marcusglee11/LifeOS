from __future__ import annotations

import subprocess
from pathlib import Path


def test_promotion_apply_direct_invocation_is_rejected() -> None:
    repo = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        ["runtime/tools/openclaw_coo_update_protocol.sh", "promotion-apply"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "internal-only" in proc.stderr.lower()
