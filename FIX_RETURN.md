# FIX_RETURN

## Validators

### validate_review_packet.py (1 PASS + 5 FAIL)

```text
PASS
FAIL REV01: Review Packet Missing
FAIL REV02: Invalid Header
FAIL REV03: Missing Sections
FAIL REV04: Invalid File Inventory
FAIL REV05: Missing Hashes
```

### validate_plan_packet.py (1 PASS + 5 FAIL)

```text
PASS
FAIL PLN01: No Plan Packet
FAIL PLN02: Invalid Header
FAIL PLN03: Missing Sections
FAIL PLN04: Unapproved changes
FAIL PLN05: Path violations
```
