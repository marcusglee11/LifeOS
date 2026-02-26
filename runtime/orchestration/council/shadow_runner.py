"""Shadow Council V2 runner — executes CouncilFSMv2 in parallel, never gates.

Runs the council runtime as a shadow to capture verdicts for comparison logging.
All exceptions are caught — shadow never affects pipeline outcome.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from runtime.util.atomic_write import atomic_write_json
from runtime.util.canonical import compute_sha256

logger = logging.getLogger(__name__)


class ShadowCouncilRunner:
    """Execute CouncilFSMv2 as shadow. Never raises to caller."""

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root)

    def run_shadow(
        self,
        run_id: str,
        ccp: Dict[str, Any],
        policy_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute CouncilFSMv2 as shadow. Returns verdict dict.

        Output is persisted to artifacts/shadow_council/<run_id>/verdict.json.
        All exceptions are caught and logged — never raises.

        Args:
            run_id: Current run identifier.
            ccp: Council Context Pack.
            policy_path: Optional path to council policy YAML.

        Returns:
            Verdict dict (also persisted to disk).
        """
        output_dir = self.repo_root / "artifacts" / "shadow_council" / run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        verdict_path = output_dir / "verdict.json"

        try:
            from runtime.orchestration.council import CouncilFSMv2, load_council_policy

            policy = load_council_policy(policy_path)
            fsm = CouncilFSMv2(policy=policy)
            result = fsm.run(ccp)

            verdict = {
                "schema_version": "shadow_council_v1",
                "run_id": run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": result.status,
                "decision_payload": result.decision_payload,
                "verdict_hash": compute_sha256(result.decision_payload),
            }

            atomic_write_json(verdict_path, verdict)
            logger.info("Shadow council verdict: %s (run_id=%s)", result.status, run_id)
            return verdict

        except Exception as exc:
            error_verdict = {
                "schema_version": "shadow_council_v1",
                "run_id": run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "shadow_error",
                "error": str(exc),
            }
            try:
                atomic_write_json(verdict_path, error_verdict)
            except Exception:
                pass  # Even persistence failure is non-fatal for shadow
            logger.warning("Shadow council error (run_id=%s): %s", run_id, exc)
            return error_verdict
