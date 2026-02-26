"""Per-invocation receipt collector for build loop runs.

Records each LLM/CLI agent invocation with timing, hashes, and validation status.
Finalizes to an index.json under artifacts/receipts/<run_id>/.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime.util.atomic_write import atomic_write_json
from runtime.util.canonical import compute_sha256


@dataclass
class InvocationReceipt:
    seq: int
    run_id: str
    provider_id: str  # "zen", "codex", "gemini", "claude_code"
    mode: str  # "api" | "cli"
    seat_id: str  # "designer", "reviewer_architect", etc.
    start_ts: str
    end_ts: str
    exit_status: int
    output_hash: str  # SHA-256 of response content
    schema_validation: str  # "pass" | "fail" | "n/a"
    token_usage: Optional[Dict[str, int]] = None
    truncation: Optional[Dict[str, bool]] = None
    error: Optional[str] = None


class InvocationReceiptCollector:
    """Collects invocation receipts during a run and finalizes to index.json."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self._receipts: List[InvocationReceipt] = []
        self._seq_counter = 0

    def record(
        self,
        provider_id: str,
        mode: str,
        seat_id: str,
        start_ts: str,
        end_ts: str,
        exit_status: int,
        output_content: str,
        schema_validation: str = "n/a",
        token_usage: Optional[Dict[str, int]] = None,
        truncation: Optional[Dict[str, bool]] = None,
        error: Optional[str] = None,
    ) -> InvocationReceipt:
        """Record a single invocation and return its receipt."""
        self._seq_counter += 1
        output_hash = compute_sha256(output_content)

        receipt = InvocationReceipt(
            seq=self._seq_counter,
            run_id=self.run_id,
            provider_id=provider_id,
            mode=mode,
            seat_id=seat_id,
            start_ts=start_ts,
            end_ts=end_ts,
            exit_status=exit_status,
            output_hash=output_hash,
            schema_validation=schema_validation,
            token_usage=token_usage,
            truncation=truncation,
            error=error,
        )
        self._receipts.append(receipt)
        return receipt

    def finalize(self, output_dir: Path) -> Path:
        """Write index.json to output_dir/artifacts/receipts/<run_id>/index.json.

        Args:
            output_dir: Repository root or base output directory.

        Returns:
            Path to the written index.json file.
        """
        receipts_dir = output_dir / "artifacts" / "receipts" / self.run_id
        receipts_dir.mkdir(parents=True, exist_ok=True)
        index_path = receipts_dir / "index.json"

        index = {
            "schema_version": "invocation_index_v1",
            "run_id": self.run_id,
            "receipt_count": len(self._receipts),
            "receipts": [asdict(r) for r in self._receipts],
        }

        atomic_write_json(index_path, index)
        return index_path

    @property
    def receipts(self) -> List[InvocationReceipt]:
        return list(self._receipts)
