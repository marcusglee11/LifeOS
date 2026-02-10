"""Deterministic reporting and atomic JSON writes."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, Mapping


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = canonical_json(payload)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def write_validator_report(report_path: Path, report_payload: Dict[str, Any]) -> None:
    if report_payload.get("pass") is not False:
        raise ValueError("validator_report.json must have pass=false")
    write_json_atomic(report_path, report_payload)


def write_acceptance_token(token_path: Path, token_payload: Dict[str, Any]) -> None:
    if token_payload.get("pass") is not True:
        raise ValueError("acceptance_token.json must have pass=true")
    if "token_sha256" in token_payload:
        raise ValueError("acceptance_token.json must not contain token_sha256")
    write_json_atomic(token_path, token_payload)
