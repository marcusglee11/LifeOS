"""
JSON Schema definitions for LifeOS receipts artefacts (v2.4).

All schemas enforce:
- additionalProperties: false (strict validation)
- _ext field for extension data
- Draft 2020-12 features (allOf/if/then/const)

Schema constants:
- ACCEPTANCE_RECEIPT_SCHEMA
- BLOCKED_REPORT_SCHEMA
- LAND_RECEIPT_SCHEMA
- GATE_RESULT_SCHEMA
- RUNLOG_EVENT_SCHEMA
- REVIEW_SUMMARY_SCHEMA
"""

# Shared artefact reference sub-schema
ARTEFACT_REF_DEF = {
    "type": "object",
    "required": ["ref_type", "location"],
    "properties": {
        "ref_type": {"type": "string", "minLength": 1},
        "location": {"type": "string", "minLength": 1},
        "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "_ext": {"type": "object"},
    },
    "additionalProperties": False,
}

# Gate result schema
GATE_RESULT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["gate_id", "status", "blocking"],
    "properties": {
        "gate_id": {"type": "string", "minLength": 1},
        "status": {"type": "string", "enum": ["PASS", "FAIL", "WARN", "BLOCKED", "SKIP"]},
        "blocking": {"type": "boolean"},
        "evidence_ref": ARTEFACT_REF_DEF,
        "_ext": {"type": "object"},
    },
    "additionalProperties": False,
}

# RunLog event schema
RUNLOG_EVENT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["phase", "step_id", "attempt_num", "seq", "timestamp", "event_type"],
    "properties": {
        "phase": {"type": "string", "minLength": 1},
        "step_id": {"type": "string", "minLength": 1},
        "attempt_num": {"type": "integer", "minimum": 0},
        "seq": {"type": "integer", "minimum": 0},
        "timestamp": {"type": "string", "format": "date-time"},
        "event_type": {"type": "string", "minLength": 1},
        "data": {"type": "object"},
        "_ext": {"type": "object"},
    },
    "additionalProperties": False,
}

# Review summary schema
REVIEW_SUMMARY_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["overall_status", "gate_count", "pass_count", "fail_count"],
    "properties": {
        "overall_status": {"type": "string", "enum": ["PASS", "FAIL", "WARN", "BLOCKED"]},
        "gate_count": {"type": "integer", "minimum": 0},
        "pass_count": {"type": "integer", "minimum": 0},
        "fail_count": {"type": "integer", "minimum": 0},
        "warn_count": {"type": "integer", "minimum": 0},
        "blocked_count": {"type": "integer", "minimum": 0},
        "skip_count": {"type": "integer", "minimum": 0},
        "evidence_manifest": {
            "type": "array",
            "items": ARTEFACT_REF_DEF,
        },
        "runlog_stats": {"type": "object"},
        "_ext": {"type": "object"},
    },
    "additionalProperties": False,
}

# Decision sub-schema used in acceptance receipt
# Uses allOf + if/then to enforce:
# - ACCEPTED MUST NOT have reason_code
# - REJECTED/BLOCKED MUST have reason_code
_DECISION_SCHEMA = {
    "type": "object",
    "required": ["status"],
    "properties": {
        "status": {"type": "string", "enum": ["ACCEPTED", "REJECTED", "BLOCKED"]},
        "reason_code": {"type": "string", "minLength": 1},
        "_ext": {"type": "object"},
    },
    "additionalProperties": False,
    "allOf": [
        {
            "if": {"properties": {"status": {"const": "ACCEPTED"}}, "required": ["status"]},
            "then": {"not": {"required": ["reason_code"]}},
        },
        {
            "if": {
                "properties": {"status": {"enum": ["REJECTED", "BLOCKED"]}},
                "required": ["status"],
            },
            "then": {"required": ["reason_code"]},
        },
    ],
}

# Policy pack sub-schema
_POLICY_PACK_SCHEMA = {
    "type": "object",
    "required": ["policy_id"],
    "properties": {
        "policy_id": {"type": "string", "minLength": 1},
        "policy_version": {"type": "string"},
        "policy_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "trusted_source": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "ref": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "_ext": {"type": "object"},
    },
    "additionalProperties": False,
}

# Acceptance receipt schema (v2.4)
ACCEPTANCE_RECEIPT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": [
        "receipt_id",
        "schema_version",
        "workspace_sha",
        "workspace_tree_oid",
        "plan_core_sha256",
        "issued_at",
        "policy_pack",
        "decision",
    ],
    "properties": {
        "receipt_id": {
            "type": "string",
            "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$",
        },
        "schema_version": {"type": "string", "const": "2.4"},
        "workspace_sha": {"type": "string", "minLength": 1},
        "workspace_tree_oid": {
            "type": "string",
            "pattern": "^[0-9a-f]{40}$",
        },
        "plan_core_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "issued_at": {"type": "string", "format": "date-time"},
        "policy_pack": _POLICY_PACK_SCHEMA,
        "decision": _DECISION_SCHEMA,
        "gate_rollup": {
            "type": "object",
            "properties": {
                "overall_status": {"type": "string"},
                "_ext": {"type": "object"},
            },
        },
        "artefact_refs": {
            "type": "array",
            "items": ARTEFACT_REF_DEF,
        },
        "supersedes": {
            "type": "string",
            "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$",
        },
        "_ext": {"type": "object"},
    },
    "additionalProperties": False,
}

# Blocked report schema (v2.4)
BLOCKED_REPORT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": [
        "report_id",
        "schema_version",
        "workspace_sha",
        "plan_core_sha256",
        "issued_at",
        "reason_code",
    ],
    "properties": {
        "report_id": {
            "type": "string",
            "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$",
        },
        "schema_version": {"type": "string", "const": "2.4"},
        "workspace_sha": {"type": "string", "minLength": 1},
        "plan_core_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "issued_at": {"type": "string", "format": "date-time"},
        "reason_code": {"type": "string", "minLength": 1},
        "gate_rollup": {
            "type": "object",
            "properties": {
                "overall_status": {"type": "string"},
                "_ext": {"type": "object"},
            },
        },
        "artefact_refs": {
            "type": "array",
            "items": ARTEFACT_REF_DEF,
        },
        "_ext": {"type": "object"},
    },
    "additionalProperties": False,
}

# Land receipt schema (v2.4)
_ACCEPTANCE_LINEAGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "acceptance_receipt_id",
        "workspace_sha",
        "workspace_tree_oid",
        "plan_core_sha256",
    ],
    "properties": {
        "acceptance_receipt_id": {"type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$"},
        "workspace_sha": {"type": "string", "pattern": "^[0-9a-f]{40}([0-9a-f]{24})?$"},
        "workspace_tree_oid": {"type": "string", "pattern": "^[0-9a-f]{40}([0-9a-f]{24})?$"},
        "plan_core_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "acceptance_ref": ARTEFACT_REF_DEF,
        "_ext": {"type": "object"},
    },
}

_TREE_EQUIVALENCE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["workspace_tree_oid", "landed_tree_oid", "match", "verified_by"],
    "properties": {
        "workspace_tree_oid": {"type": "string", "pattern": "^[0-9a-f]{40}([0-9a-f]{24})?$"},
        "landed_tree_oid": {"type": "string", "pattern": "^[0-9a-f]{40}([0-9a-f]{24})?$"},
        "match": {"type": "boolean"},
        "verified_by": {"enum": ["land_emitter", "reconciliation_job"]},
        "_ext": {"type": "object"},
    },
}

_LAND_EMITTER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["agent_id", "run_id"],
    "properties": {
        "agent_id": {"type": "string", "minLength": 1},
        "run_id": {"type": "string", "minLength": 1},
        "environment": {"type": "string"},
        "_ext": {"type": "object"},
    },
}

LAND_RECEIPT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "receipt_id",
        "schema_version",
        "receipt_type",
        "created_at",
        "landed_sha",
        "landed_tree_oid",
        "land_target",
        "merge_method",
        "acceptance_lineage",
        "tree_equivalence",
        "emitter",
    ],
    "properties": {
        "receipt_id": {"type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$"},
        "schema_version": {"const": "land_receipt.v2.4"},
        "receipt_type": {"const": "land"},
        "created_at": {"type": "string", "format": "date-time"},
        "landed_sha": {"type": "string", "pattern": "^[0-9a-f]{40}([0-9a-f]{24})?$"},
        "landed_tree_oid": {"type": "string", "pattern": "^[0-9a-f]{40}([0-9a-f]{24})?$"},
        "land_target": {"type": "string", "minLength": 1},
        "merge_method": {"enum": ["merge", "squash", "rebase", "fast-forward"]},
        "acceptance_lineage": _ACCEPTANCE_LINEAGE_SCHEMA,
        "tree_equivalence": _TREE_EQUIVALENCE_SCHEMA,
        "emitter": _LAND_EMITTER_SCHEMA,
        "landing_evidence": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "merge_api_response_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                "_ext": {"type": "object"},
            },
        },
        "_ext": {"type": "object"},
    },
}
