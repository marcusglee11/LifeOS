from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

FORBIDDEN_NEXT_STEPS = [
    "implementation_without_reload",
    "additive_or_polish_framing_if_source_requires_absence",
    "reviewer_output_as_authority",
    "compression_as_canonical_memory",
]
NOT_AUTHORIZED_FOR = [
    "external_send",
    "runtime_activation",
    "credential_change",
    "destructive_cleanup",
]
CEO_ONLY_BYPASS_TERMS = {
    "absence",
    "destructive",
    "irreversible",
    "reversibility",
    "privacy",
    "externality",
    "automation_boundary",
    "approval_before_action",
}


@dataclass
class ConductorVerification:
    schema_version: str
    work_item_id: str
    brief_type: str
    brief_hash_sha256: str
    brief_author_session: str
    conductor_verification_session: str
    source_manifest_hash_sha256: str
    fidelity_report_hash_sha256: str
    conductor_independently_confirmed: bool
    fidelity_status: str
    handoff_candidate: bool
    implementation_authority_granted: bool
    required_next_gate: str
    forbidden_next_steps: list[str]
    verified_by: str
    verified_at: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _required_next_gate(fidelity_status: str) -> str:
    if fidelity_status == "preserved_intent":
        return "dispatch_gate"
    if fidelity_status == "warning_only":
        return "dispatch_gate"
    if fidelity_status == "needs_clarification":
        return "ceo_clarification"
    if fidelity_status == "not_preserved":
        return "ceo_clarification"
    if fidelity_status == "requires_review":
        return "ceo_approval"
    return "none"


def build_conductor_verification(
    work_item_id: str,
    brief_type: str,
    brief_hash: str,
    brief_author_session: str,
    conductor_session: str,
    source_manifest_hash: str,
    fidelity_report_hash: str,
    fidelity_status: str,
    conductor_independently_confirmed: bool = True,
) -> ConductorVerification:
    """
    Build a conductor verification artifact.

    v0.3 never grants implementation authority.
    """
    handoff_candidate = (
        brief_author_session != conductor_session
        and conductor_independently_confirmed
        and fidelity_status in {"preserved_intent", "warning_only"}
    )
    return ConductorVerification(
        schema_version="conductor_fidelity_verification.v1",
        work_item_id=work_item_id,
        brief_type=brief_type,
        brief_hash_sha256=brief_hash,
        brief_author_session=brief_author_session,
        conductor_verification_session=conductor_session,
        source_manifest_hash_sha256=source_manifest_hash,
        fidelity_report_hash_sha256=fidelity_report_hash,
        conductor_independently_confirmed=conductor_independently_confirmed,
        fidelity_status=fidelity_status,
        handoff_candidate=handoff_candidate,
        implementation_authority_granted=False,
        required_next_gate=_required_next_gate(fidelity_status),
        forbidden_next_steps=list(FORBIDDEN_NEXT_STEPS),
        verified_by="conductor",
        verified_at=_now_iso(),
    )


_bypass_registry: dict[str, dict] = {}


@dataclass
class BypassRecord:
    schema_version: str
    work_item_id: str
    requested_by: str
    authorized_by: str
    reason: str
    sources_skipped: list[str]
    risk_accepted: str
    scope: str
    expires_at: str
    single_use: bool
    not_authorized_for: list[str]
    _used: bool = False


def _record_to_public_dict(record: BypassRecord) -> dict:
    payload = asdict(record)
    payload.pop("_used", None)
    return payload


def _bypass_id(record: BypassRecord) -> str:
    payload = json.dumps(_record_to_public_dict(record), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _requires_ceo_authorization(scope: str, admissible_missing_policy: str | None) -> bool:
    material = f"{scope} {admissible_missing_policy or ''}".lower()
    return any(term in material for term in CEO_ONLY_BYPASS_TERMS)


def create_bypass(
    work_item_id: str,
    requested_by: str,
    authorized_by: str,
    reason: str,
    scope: str,
    admissible_missing_policy: str | None = None,
) -> str:
    """
    Create a bypass record.

    Bypass is local, single-use, and capped at 24 hours. CEO-only classes require
    `authorized_by="ceo"`.
    """
    if authorized_by not in {"conductor", "ceo"}:
        raise ValueError("authorized_by must be conductor or ceo")
    if authorized_by != "ceo" and _requires_ceo_authorization(scope, admissible_missing_policy):
        raise ValueError("CEO approval required for this bypass scope")

    expires_at = (_now() + timedelta(hours=24)).isoformat()
    record = BypassRecord(
        schema_version="intent_fidelity_bypass.v1",
        work_item_id=work_item_id,
        requested_by=requested_by,
        authorized_by=authorized_by,
        reason=reason,
        sources_skipped=[],
        risk_accepted=admissible_missing_policy or "warning-only or known false-positive risk",
        scope=scope,
        expires_at=expires_at,
        single_use=True,
        not_authorized_for=list(NOT_AUTHORIZED_FOR),
    )
    bypass_id = _bypass_id(record)
    _bypass_registry[bypass_id] = asdict(record)
    return bypass_id


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def check_bypass_valid(bypass_id: str) -> tuple[bool, str]:
    """
    Check if a bypass is valid at the current time.
    Returns (is_valid, reason).
    Fails if expired, already used, or not found.
    """
    record = _bypass_registry.get(bypass_id)
    if record is None:
        return False, "not_found"
    if record.get("_used"):
        return False, "already_used"
    if _parse_iso(record["expires_at"]) <= _now():
        return False, "expired"
    return True, "valid"


def use_bypass(bypass_id: str) -> tuple[bool, str]:
    """
    Mark a bypass as used (consumes single_use).
    Returns (success, message).
    """
    valid, reason = check_bypass_valid(bypass_id)
    if not valid:
        return False, reason
    _bypass_registry[bypass_id]["_used"] = True
    return True, "used"


def get_active_bypasses() -> list[dict]:
    """Get all currently valid (non-expired, non-used) bypass records."""
    active: list[dict] = []
    for bypass_id, record in _bypass_registry.items():
        valid, _reason = check_bypass_valid(bypass_id)
        if valid:
            active.append({key: value for key, value in record.items() if key != "_used"})
    return active
