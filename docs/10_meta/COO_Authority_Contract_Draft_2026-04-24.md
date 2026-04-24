# COO Authority Contract Draft — 2026-04-24

Status: Draft for normalization decision
Owner: CEO
Purpose: Settle authority, mutation, and escalation boundaries needed before further COO onboarding cleanup
Related input: `docs/10_meta/Architecture_Normalization_Reconciliation_Packet_2026-04-24.md`

---

## 1. Human approval form

Draft resolution:
- Authoritative CEO approval is channel-agnostic at source but not at storage.
- Allowed source channels for now: Telegram and CLI.
- Approval becomes authoritative only when the active COO captures it into an approval receipt linked to the relevant proposal / work item.

Minimum captured approval record:
- `proposal_id`
- `proposal_fingerprint`
- `rendered_summary_hash`
- `approval_action`
- `captured_from_channel`
- `captured_at`
- `captured_by = active_coo`
- `policy_version` when policy gating participated
- `phase` when phase-dependent authority mattered

Reason:
- This preserves `LifeOS Target Architecture v2.3c` channel flexibility while adopting the communications draft requirement that approvals do not directly mutate GitHub state.

## 2. Proxy / delegated authority

Draft resolution:
- CEO authority is not transferable.
- COO substrates may exercise delegated operational authority only within currently ratified phase / policy boundaries.
- Proxy authority may recommend, classify, validate, and escalate.
- Proxy authority may authorize operational mutation only when that mutation is already permitted by ratified delegation rules and captured policy, not by ad hoc conversational delegation.

Reason:
- Prevents hidden expansion of authority during onboarding or substrate swaps.

## 3. Active vs standby COO semantics

Draft resolution:
- Exactly one COO substrate is active writer at a time.
- Active COO alone may mutate operational GitHub state, emit approval / promotion / reconciliation / completion receipts, and consume forwarded Commons events.
- Standby COO may observe, verify, rehearse, and assess readiness, but may not mutate operational state while standby.
- Activation occurs only through explicit switchover:
  1. stop forwarding to active
  2. drain in-flight deliveries
  3. quiesce mutation workers
  4. verify no open decision cycle
  5. activate standby
  6. resume forwarding
  7. log switchover event

Reason:
- This matches current canonical v2.3c semantics and removes ambiguity during dual-COO onboarding.

## 4. Inter-agent directionality

Draft resolution:
- Hermes and OpenClaw may exchange advisory instructions, challenge packets, or rehearsal guidance.
- Neither COO may unilaterally issue authoritative direction to the other while both are peers in substrate candidacy / standby-active topology.
- Any cross-COO direction that would cause operational mutation must be re-issued through the active COO authority path or escalated to CEO.
- Pushback is always permitted when authority, phase, approval, or writer boundaries are unclear.

Reason:
- Prevents a hidden second control plane.

## 5. Sole-writer boundaries

Draft resolution:
- Sole-writer rule applies to all operational state, not only the GitHub issue state block.
- Operational state includes:
  - work-order issue body + state block
  - labels when used for routing / status
  - Projects v2 projections
  - approval receipts
  - promotion receipts
  - reconciliation receipts
  - completion / closure receipts
- Shared-write is not allowed for operational state in Phase 1 normalization.
- EAs remain evidence writers only: PRs, commits, structured result comments.
- Advisory surfaces remain ingress-only and non-operational.

Reason:
- Current canon already trends this way; making it explicit closes ambiguity.

## 6. Approval binding tuple

Draft resolution:
- Minimum binding tuple is:
  - `proposal_id`
  - `proposal_fingerprint`
  - `rendered_summary_hash`
- Required contextual extensions when applicable:
  - `policy_version`
  - `phase`

Interpretation:
- If any bound element changes before promotion, approval is invalid and fresh approval is required.

## 7. Deferred questions that should not block normalization

1. Whether `briefing/current.md` is retained as a formal projection surface.
2. Whether Google Workspace / `gws` becomes canonical as advisory ingress infrastructure or remains a convenience adapter outside canon.
3. Whether advisory ingress should remain split across GitHub advisory issues and Drive proposal files.

## 8. Recommended ratification sequence

1. Ratify approval form + capture rule.
2. Ratify active/standby + sole-writer boundaries.
3. Ratify cross-COO directionality.
4. Then reconcile architecture docs and open implementation issues.
