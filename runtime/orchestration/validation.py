"""
Gate validation for mission and packet schemas.
"""
from pathlib import Path
import yaml
from jsonschema import Draft7Validator

SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "config" / "schemas"

class GateValidationError(Exception):
    pass


def _load_schema(name: str) -> dict:
    path = SCHEMA_ROOT / name
    if not path.exists():
        raise GateValidationError(f"Schema not found: {name}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def gate_check(payload: dict, schema_name: str) -> None:
    schema = _load_schema(schema_name)
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    if errors:
        messages = []
        for e in errors:
            loc = "/".join([str(p) for p in e.path]) or "<root>"
            messages.append(f"{loc}: {e.message}")
        raise GateValidationError("; ".join(messages))

    return None
