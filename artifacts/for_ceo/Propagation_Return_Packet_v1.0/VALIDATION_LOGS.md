# Propagation Validation Logs

### validate_review_packet.py (1 PASS + 5 FAIL)
```text
> C:\Python312\python.exe scripts/validate_review_packet.py tests/fixtures/review_packet\pass_01.md
PASS
> C:\Python312\python.exe scripts/validate_review_packet.py tests/fixtures/review_packet\fail_RPV001.md
FAIL RPV001: Missing section 'Scope Envelope'.
> C:\Python312\python.exe scripts/validate_review_packet.py tests/fixtures/review_packet\fail_RPV002.md
FAIL RPV002: Section 'Summary' found before previous section.
> C:\Python312\python.exe scripts/validate_review_packet.py tests/fixtures/review_packet\fail_RPV003.md
FAIL RPV003: Acceptance Criteria table missing column 'evidence pointer'. Found: ['id', 'criterion', 'status', 'sha-256']
> C:\Python312\python.exe scripts/validate_review_packet.py tests/fixtures/review_packet\fail_RPV004.md
FAIL RPV004: Invalid Evidence Pointer 'bad pointer' (must be path | path:Lx-Ly | path#sha256:<HEX64> | N/A(<reason>)).
> C:\Python312\python.exe scripts/validate_review_packet.py tests/fixtures/review_packet\fail_RPV005.md
FAIL RPV005: Missing mandatory checklist row 'Provenance'.
```

### validate_plan_packet.py (1 PASS + 5 FAIL)
```text
> C:\Python312\python.exe scripts/validate_plan_packet.py tests/fixtures/plan_packet\pass_01.md
PASS
> C:\Python312\python.exe scripts/validate_plan_packet.py tests/fixtures/plan_packet\fail_PPV001.md
FAIL PPV001: Missing required section 'Scope Envelope' in PLAN_PACKET.
> C:\Python312\python.exe scripts/validate_plan_packet.py tests/fixtures/plan_packet\fail_PPV002.md
FAIL PPV002: PLAN_PACKET section order invalid. Expected: Scope Envelope -> Proposed Changes -> Claims -> Targets -> Validator Contract -> Verification Matrix -> Migration Plan -> Governance Impact.
> C:\Python312\python.exe scripts/validate_plan_packet.py tests/fixtures/plan_packet\fail_PPV003.md
FAIL PPV003: Claim 'C' marked proven but evidence pointer missing.
> C:\Python312\python.exe scripts/validate_plan_packet.py tests/fixtures/plan_packet\fail_PPV005.md
FAIL PPV005: Claim 'C' marked proven but evidence file not found at 'nonexistent_file.md'.
> C:\Python312\python.exe scripts/validate_plan_packet.py tests/fixtures/plan_packet\fail_PPV006.md
FAIL PPV006: Verification Matrix insufficient (need >=1 PASS and >=5 FAIL with distinct codes; found PASS=1, FAIL_DISTINCT=4).
```
