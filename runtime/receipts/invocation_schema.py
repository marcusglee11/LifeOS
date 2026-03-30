"""JSON Schema definitions for invocation receipts and index (Draft 2020-12)."""

INVOCATION_RECEIPT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "seq",
        "run_id",
        "provider_id",
        "mode",
        "seat_id",
        "start_ts",
        "end_ts",
        "exit_status",
        "output_hash",
        "schema_validation",
    ],
    "properties": {
        "seq": {"type": "integer", "minimum": 1},
        "run_id": {"type": "string", "minLength": 1},
        "provider_id": {"type": "string", "minLength": 1},
        "mode": {"type": "string", "enum": ["api", "cli"]},
        "seat_id": {"type": "string", "minLength": 1},
        "start_ts": {"type": "string", "format": "date-time"},
        "end_ts": {"type": "string", "format": "date-time"},
        "exit_status": {"type": "integer"},
        "output_hash": {"type": "string", "minLength": 1},
        "schema_validation": {"type": "string", "enum": ["pass", "fail", "n/a"]},
        "token_usage": {
            "type": ["object", "null"],
            "properties": {
                "prompt_tokens": {"type": "integer", "minimum": 0},
                "completion_tokens": {"type": "integer", "minimum": 0},
                "total_tokens": {"type": "integer", "minimum": 0},
            },
        },
        "truncation": {
            "type": ["object", "null"],
            "properties": {
                "input_truncated": {"type": "boolean"},
                "output_truncated": {"type": "boolean"},
            },
        },
        "error": {"type": ["string", "null"]},
        "input_hash": {"type": ["string", "null"]},  # Phase 4A: SHA-256 of input prompt/packet
    },
}

INVOCATION_INDEX_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "run_id", "receipt_count", "receipts"],
    "properties": {
        "schema_version": {"type": "string", "const": "invocation_index_v1"},
        "run_id": {"type": "string", "minLength": 1},
        "receipt_count": {"type": "integer", "minimum": 0},
        "receipts": {
            "type": "array",
            "items": INVOCATION_RECEIPT_SCHEMA,
        },
    },
}
