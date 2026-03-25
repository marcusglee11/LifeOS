from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from runtime.util.atomic_write import atomic_write_text


class OperationQueueError(ValueError):
    pass


_OPS_BASE = Path("artifacts") / "coo" / "operations"


def _ops_base(repo_root: Path) -> Path:
    return repo_root / _OPS_BASE


def _ops_dir(repo_root: Path, lane: str) -> Path:
    path = _ops_base(repo_root) / lane
    path.mkdir(parents=True, exist_ok=True)
    return path


def _yaml_dump(payload: dict[str, Any]) -> str:
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)


def _persist_yaml(repo_root: Path, lane: str, record_id: str, payload: dict[str, Any]) -> Path:
    path = _ops_dir(repo_root, lane) / f"{record_id}.yaml"
    atomic_write_text(path, _yaml_dump(payload))
    return path


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise OperationQueueError(f"Missing operations artifact: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise OperationQueueError(f"Operations artifact must be a YAML mapping: {path}")
    return raw


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def persist_operation_proposal(repo_root: Path, payload: dict[str, Any]) -> Path:
    proposal_id = str(payload.get("proposal_id", "")).strip()
    if not proposal_id:
        raise OperationQueueError("proposal payload missing proposal_id")
    return _persist_yaml(repo_root, "proposals", proposal_id, payload)


def load_operation_proposal(repo_root: Path, proposal_id: str) -> dict[str, Any]:
    return _load_yaml(_ops_dir(repo_root, "proposals") / f"{proposal_id}.yaml")


def persist_operational_order(repo_root: Path, payload: dict[str, Any]) -> Path:
    order_id = str(payload.get("order_id", "")).strip()
    if not order_id:
        raise OperationQueueError("order payload missing order_id")
    return _persist_yaml(repo_root, "orders", order_id, payload)


def persist_operational_receipt(repo_root: Path, payload: dict[str, Any]) -> Path:
    receipt_id = str(payload.get("receipt_id", "")).strip()
    if not receipt_id:
        raise OperationQueueError("receipt payload missing receipt_id")
    return _persist_yaml(repo_root, "receipts", receipt_id, payload)


def save_proposal(repo_root: Path, payload: dict[str, Any]) -> Path:
    return persist_operation_proposal(repo_root, payload)


def load_proposal(repo_root: Path, proposal_id: str) -> dict[str, Any]:
    return load_operation_proposal(repo_root, proposal_id)


def save_order(repo_root: Path, payload: dict[str, Any]) -> Path:
    return persist_operational_order(repo_root, payload)


def save_receipt(repo_root: Path, payload: dict[str, Any]) -> Path:
    return persist_operational_receipt(repo_root, payload)


def find_receipt_by_proposal_id(repo_root: Path, proposal_id: str) -> dict[str, Any] | None:
    receipts_dir = _ops_dir(repo_root, "receipts")
    for path in sorted(receipts_dir.glob("OPRCP-*.yaml")):
        raw = _load_yaml(path)
        if str(raw.get("proposal_id", "")).strip() == proposal_id:
            return raw
    return None
