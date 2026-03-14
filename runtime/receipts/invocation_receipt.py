"""Per-invocation receipt collector for build loop runs.

Records each LLM/CLI agent invocation with timing, hashes, and validation status.
Finalizes to an index.json under artifacts/receipts/<run_id>/.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional
import re

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
    input_hash: Optional[str] = None  # SHA-256 of input prompt/packet (Phase 4A)


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
        input_hash: Optional[str] = None,
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
            input_hash=input_hash,
        )
        self._receipts.append(receipt)
        return receipt

    def finalize(self, output_dir: Path) -> Path:
        """Write receipts and index to output_dir/artifacts/receipts/<run_id>/.

        Args:
            output_dir: Repository root or base output directory.

        Returns:
            Path to the written index.json file.
        """
        receipts_dir = output_dir / "artifacts" / "receipts" / self.run_id
        receipts_dir.mkdir(parents=True, exist_ok=True)
        index_path = receipts_dir / "index.json"

        for receipt in self._receipts:
            receipt_path = receipts_dir / self._receipt_filename(receipt)
            atomic_write_json(receipt_path, asdict(receipt))

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

    @staticmethod
    def _receipt_filename(receipt: InvocationReceipt) -> str:
        provider = re.sub(r"[^a-zA-Z0-9._-]+", "_", receipt.provider_id.strip())
        provider = provider or "unknown"
        return f"{receipt.seq:04d}_{provider}.json"


_COLLECTORS: Dict[str, InvocationReceiptCollector] = {}
_COLLECTORS_LOCK = Lock()


def get_or_create_collector(run_id: str) -> InvocationReceiptCollector:
    """Get run collector, creating one if missing."""
    with _COLLECTORS_LOCK:
        collector = _COLLECTORS.get(run_id)
        if collector is None:
            collector = InvocationReceiptCollector(run_id=run_id)
            _COLLECTORS[run_id] = collector
        return collector


def record_invocation_receipt(
    run_id: str,
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
    input_hash: Optional[str] = None,
) -> Optional[InvocationReceipt]:
    """Record an invocation receipt for a run. No-op if run_id is empty."""
    if not run_id:
        return None

    collector = get_or_create_collector(run_id)
    return collector.record(
        provider_id=provider_id,
        mode=mode,
        seat_id=seat_id,
        start_ts=start_ts,
        end_ts=end_ts,
        exit_status=exit_status,
        output_content=output_content,
        schema_validation=schema_validation,
        token_usage=token_usage,
        truncation=truncation,
        error=error,
        input_hash=input_hash,
    )


def finalize_run_receipts(
    run_id: str,
    output_dir: Path,
    include_empty: bool = False,
) -> Optional[Path]:
    """Finalize and remove collector for a run, returning index path if written."""
    if not run_id:
        return None

    with _COLLECTORS_LOCK:
        collector = _COLLECTORS.pop(run_id, None)

    if collector is None:
        if not include_empty:
            return None
        collector = InvocationReceiptCollector(run_id=run_id)

    return collector.finalize(output_dir=output_dir)


def reset_invocation_receipt_collectors() -> None:
    """Test helper: clear in-memory collector registry."""
    with _COLLECTORS_LOCK:
        _COLLECTORS.clear()
