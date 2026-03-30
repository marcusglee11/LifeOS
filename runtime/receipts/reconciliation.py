"""
Phase C reconciliation job — audit mode (spec §10.2).

Checks each landed_sha for a valid land receipt with tree_equivalence.match=True.
Audit mode: log only, no blocking.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runtime.receipts.store import ReceiptStore


@dataclass(frozen=True)
class ReconciliationReport:
    """Result of a reconciliation run."""

    total_checked: int
    compliant: int  # land receipt exists + match=True
    bypasses: int  # no land receipt found
    violations: int  # land receipt exists but match=False
    findings: list[dict[str, Any]]
    mode: str  # "audit" | "alert" | "enforce"


def run_reconciliation(
    landed_shas: list[str],
    store_root: Path | str,
    mode: str = "audit",
) -> ReconciliationReport:
    """
    Reconcile a list of landed SHAs against the store (spec §10.2).

    For each landed_sha:
    - COMPLIANT: land receipt exists and tree_equivalence.match=True
    - BYPASS: no land receipt found
    - VIOLATION: land receipt exists but tree_equivalence.match=False

    Args:
        landed_shas: List of merge commit SHAs to check.
        store_root: Path to the receipt store.
        mode: "audit" (log only), "alert", or "enforce".

    Returns:
        ReconciliationReport with counts and per-SHA findings.
    """
    if mode not in {"audit", "alert", "enforce"}:
        raise ValueError(f"Unsupported reconciliation mode: {mode!r}")

    store = ReceiptStore(store_root)
    findings: list[dict[str, Any]] = []
    compliant = bypasses = violations = 0

    for sha in landed_shas:
        receipt = store.query_land_receipt_by_landed_sha(sha)
        if receipt is None:
            bypasses += 1
            findings.append(
                {"landed_sha": sha, "status": "BYPASS", "detail": "No land receipt found"}
            )
        else:
            tree_match = receipt.get("tree_equivalence", {}).get("match")
            if tree_match is True:
                compliant += 1
                findings.append(
                    {
                        "landed_sha": sha,
                        "status": "COMPLIANT",
                        "receipt_id": receipt.get("receipt_id"),
                    }
                )
            else:
                violations += 1
                if tree_match is False:
                    detail = "tree_equivalence.match=False"
                else:
                    detail = "tree_equivalence.match missing or invalid"
                findings.append(
                    {
                        "landed_sha": sha,
                        "status": "VIOLATION",
                        "receipt_id": receipt.get("receipt_id"),
                        "detail": detail,
                    }
                )

    return ReconciliationReport(
        total_checked=len(landed_shas),
        compliant=compliant,
        bypasses=bypasses,
        violations=violations,
        findings=findings,
        mode=mode,
    )
