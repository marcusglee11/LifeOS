# OpenCode Governance Service (Phase 1)

Minimal governance service skeleton for LifeOS using a deterministic request/response model.

## Usage

Canonical entrypoint is `opencode_governance.invoke(request)`.

```python
from opencode_governance import invoke

request = {
    "version": "1.0",
    "request_id": "req-123",
    "payload": {"key": "value"}
}
response = invoke(request)
# -> {"status": "OK", "request_id": "req-123", "output": {...}, "output_hash": "..."}
```

## Contract
- **Version**: Must be `"1.0"`.
- **Determinism**: `output_hash` is SHA256 of canonical JSON (sorted keys + separators) of `output`.

## Development

**Run Tests**:
```bash
pytest runtime/tests/test_opencode_governance/ -v
```

**Steward Validation**:
```bash
python -m doc_steward.cli opencode-validate .
```

**Evidence Capture**:
Uses `scripts/steward_runner.py` via `DeterministicLogger` to ensure non-eliding capture.
See `runtime/tests/test_opencode_governance/test_phase1_contract.py` (T5) for canonical usage.
