# How to Write a Plan that Passes Preflight (PLAN_PACKET)

## 1. Structure is Strict

Your plan **must** follow the exact section order:

1. `Scope Envelope`
2. `Proposed Changes`
3. `Claims`
4. `Targets`
5. `Validator Contract`
6. `Verification Matrix`
7. `Migration Plan`
8. `Governance Impact`

**Failure Code**: `PPV002`

## 2. Claims Need Evidence

If you make a `policy_mandate` or `canonical_path` claim, you **must** provide an Evidence Pointer.

* **Format**: `path/to/file:L10-L20` or `path#sha256:HEX` or `N/A(reason)` (proposals only).
* **Invalid**: `N/A`, `Just trust me`, `See existing code`.

**Failure Code**: `PPV003`, `PPV004`

## 3. Targets via Discovery

Do not hardcode paths unless strictly necessary. Use discovery queries in your execution steps, but if you must use `fixed_path` in a target, you must back it up with a `canonical_path` claim.

## 4. Validator Contract

You must explicitly confirm the output format:

```markdown
# Validator Contract
- **Output Format**: PASS/FAIL
- **Failure Codes**: ...
```

**Failure Code**: `PPV007`
