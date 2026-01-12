# Evidence Commands and Outputs
**Run ID**: audit_verify_t5

## 1. Canonical Runner Invocation
**Config File**: `artifacts/evidence/steward_runner_config_audit_verify_t5.yaml`
**Command**:
```bash
python scripts/steward_runner.py --config artifacts/evidence/steward_runner_config_audit_verify_t5.yaml --run-id audit_verify_t5 --step validators
```

## 2. Line Count Proof
**Command**:
```bash
python -c "import sys; print(sum(1 for _ in open(sys.argv[1])), sys.argv[1])" "artifacts/evidence/b3be8cf794d6449c88da087a6545c774463d4b2802848fe0f23671e53c42c4e1.out"
```
**Output**:
```text

```

## 3. Excerpt Extraction Proof
**Command**:
```bash
python -c "lines=open('artifacts/evidence/b3be8cf794d6449c88da087a6545c774463d4b2802848fe0f23671e53c42c4e1.out').readlines(); print(''.join(lines[:3] + lines[-3:]), end='')"
```
**Output**:
```text

```
