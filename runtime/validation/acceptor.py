"""Trusted acceptance token verifier and recorder."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict

from runtime.validation.reporting import sha256_file, write_json_atomic


class AcceptanceTokenError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


REQUIRED_TOKEN_FIELDS = {
    "schema_version",
    "pass",
    "run_id",
    "attempt_id",
    "attempt_index",
    "gate_pipeline_version",
    "evidence_manifest_sha256",
    "receipt_sha256",
    "created_at",
    "provenance",
}


def _load_token(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        token = json.load(handle)
    if not isinstance(token, dict):
        raise AcceptanceTokenError("ACCEPTANCE_TOKEN_INVALID", "Token payload must be an object")
    return token


def _verify_token_shape(token: Dict[str, Any]) -> None:
    if "token_sha256" in token:
        raise AcceptanceTokenError(
            "ACCEPTANCE_TOKEN_INVALID",
            "acceptance_token.json must not include token_sha256",
        )

    missing = sorted(REQUIRED_TOKEN_FIELDS - set(token.keys()))
    if missing:
        raise AcceptanceTokenError("ACCEPTANCE_TOKEN_INVALID", f"Token missing required fields: {missing}")

    if token.get("schema_version") != "acceptance_token_v1":
        raise AcceptanceTokenError("ACCEPTANCE_TOKEN_INVALID", "Unsupported token schema")

    if token.get("pass") is not True:
        raise AcceptanceTokenError("ACCEPTANCE_TOKEN_INVALID", "Token pass must be true")

    provenance = token.get("provenance")
    if not isinstance(provenance, dict):
        raise AcceptanceTokenError("ACCEPTANCE_TOKEN_INVALID", "Token provenance must be an object")

    for key in ("manifest_path", "receipt_path", "attempt_dir"):
        if key not in provenance:
            raise AcceptanceTokenError("ACCEPTANCE_TOKEN_INVALID", f"Token provenance missing {key}")


def accept(
    acceptance_token_path: Path,
    acceptance_record_path: Path | None = None,
) -> Dict[str, Any]:
    token = _load_token(acceptance_token_path)
    _verify_token_shape(token)

    provenance = token["provenance"]
    manifest_path = Path(provenance["manifest_path"])
    receipt_path = Path(provenance["receipt_path"])

    if not manifest_path.exists():
        raise AcceptanceTokenError("ACCEPTANCE_TOKEN_INVALID", "Referenced manifest_path does not exist")

    manifest_sha = sha256_file(manifest_path)
    if manifest_sha != token["evidence_manifest_sha256"]:
        raise AcceptanceTokenError(
            "ACCEPTANCE_TOKEN_INVALID",
            "Manifest hash mismatch between token and disk",
        )

    receipt_sha = token.get("receipt_sha256")
    if receipt_sha is not None:
        if not receipt_path.exists():
            raise AcceptanceTokenError(
                "ACCEPTANCE_TOKEN_INVALID",
                "receipt_sha256 provided but receipt_path is missing",
            )
        disk_receipt_sha = sha256_file(receipt_path)
        if disk_receipt_sha != receipt_sha:
            raise AcceptanceTokenError(
                "ACCEPTANCE_TOKEN_INVALID",
                "Receipt hash mismatch between token and disk",
            )

    acceptance_token_sha256 = sha256_file(acceptance_token_path)

    record = {
        "schema_version": "acceptance_record_v1",
        "accepted": True,
        "run_id": token["run_id"],
        "attempt_id": token["attempt_id"],
        "attempt_index": token["attempt_index"],
        "accepted_at": datetime.now(timezone.utc).isoformat(),
        "token_path": str(acceptance_token_path),
        "manifest_path": str(manifest_path),
        "receipt_path": str(receipt_path),
        "evidence_manifest_sha256": token["evidence_manifest_sha256"],
        "receipt_sha256": receipt_sha,
        "acceptance_token_sha256": acceptance_token_sha256,
    }

    if acceptance_record_path is None:
        acceptance_record_path = acceptance_token_path.parent / "acceptance_record.json"
    write_json_atomic(acceptance_record_path, record)
    return record
