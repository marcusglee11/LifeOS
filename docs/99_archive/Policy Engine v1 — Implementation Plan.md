 # Policy Engine v1 — Implementation Plan (FINAL)
  **Version:** v1.2
  **Status:** IMPLEMENTATION-READY (FINAL)
  **Scope:** Tool-policy + Loop-policy governance boundary for Tier-3 readiness
  **Constitutional alignment:** CSO Role Constitution v1.3.3 (authority tiers, posture semantics,
  external comms hard-gate, fail-closed preconditions)

  ---

  ## 1. Objective

  Deliver a deterministic, fail-closed **Policy Engine** that:
  1) Governs **tool actions** (ALLOW / DENY / ESCALATE) using schema-validated YAML rules.
  2) Governs **loop outcomes** (RETRY / TERMINATE / ESCALATE) using **mandatory failure
  classification**.
  3) Implements an **end-to-end escalation loop** (create → notify → resolve → enforce) that is
  autonomy-safe (throttled, categorized, measurable).
  4) Produces audit/metrics without hot-path I/O thrash (buffered writers).
  5) Conforms to CSO v1.3.3 authority boundaries:
  - Strategic/Significant: CEO-only (via CDP outcome pathway).
  - Standard/Routine: CSO may decide only within envelope and with required evidence/logging.
  - External comms: disabled unless a CEO-authorised CE exists; drafts must be watermarked “DRAFT /
  UNAPPROVED”.

  ---

  ## 2. Non-goals (hard boundaries)

  - No attempt to prove global logical consistency of all rules (bounded conflict checks only).
  - No Jira/GitHub ticketing integration (file-based escalation queue only).
  - No distributed metrics aggregation beyond a local Prometheus exposition endpoint (optional) +
  JSONL.
  - No “agent self-reporting” of privileged context (mission_type, agent_tier are injected by
  orchestrator only).
  - No bypass of CSO v1.3.3: policy posture changes that loosen governance are not silently allowed.

  ---

  ## 3. Core invariants (binding)

  ### 3.1 Governance and authority invariants (CSO-aligned)
  I1. **Tier authority is enforced**:
  - Any Strategic/Significant decision surface must route to **CEO** (ceo_approval / CDP outcome).
  - CSO approvals are valid only for Standard/Routine within envelope; proxy approvals must be
  time-bounded (PD-like TTL) and non-precedential.

  I2. **Posture is tunable but governed**:
  - Posture parameters have **safe defaults** (used if posture missing) and **safe ranges**
  (out-of-range is prohibited).
  - Any **loosening** posture change is Significant and requires CEO (CDP outcome); tightening is
  Standard (logged).

  I3. **External comms hard gate**:
  - Any “external comms” tool surface is DENY unless an active CEO-authorised CE is provided as a
  precondition.
  - If CE absent and a draft is produced, it must be watermarked “DRAFT / UNAPPROVED”.

  ### 3.2 Determinism and fail-closed invariants
  I4. **Deterministic outcomes**:
  - Same trusted context + same rules → same policy outcome fields (decision, matched_rule_id,
  escalation_type/category/fallback), excluding non-semantic identifiers (audit_id, timestamps).

  I5. **Fail-closed preconditions**:
  - If config/schema validation cannot be performed: startup abort (fail-closed).
  - If posture is present but out-of-range: posture-dependent decisions are blocked and escalated;
  values do not take effect silently.
  - If escalation resolution is malformed/unauthorised: treated as invalid; decision remains pending
  until timeout, then fallback applies.

  ---

  ## 4. Architecture

  ### 4.1 Repo layout (deterministic paths)
  ```

  config/policy/
  policy_rules.yaml
  variables.yaml
  posture.yaml
  failure_classes.yaml
  tool_rules.yaml
  loop_rules.yaml
  schemas/
  policy_rules.schema.json
  variables.schema.json
  posture.schema.json
  failure_classes.schema.json

  runtime/governance/
  policy_registry.py
  policy_engine.py
  policy_loader.py
  policy_types.py
  policy_context.py
  policy_specificity.py
  policy_conflict.py
  path_validator.py
  escalation_handler.py
  governance_cli.py
  result_classifier.py
  audit_writer.py
  metrics.py

  runtime/orchestration/
  tool_policy_adapter.py
  loop_policy_adapter.py

  ```

  ### 4.2 Process model (fixes “singleton SPOF”)
  - **PolicyRegistry (process-scoped):** loads and validates configs once; holds immutable compiled
  rule sets.
  - **PolicyEngine (mission-scoped):** created per mission_id; holds per-mission state (pending
  budgets, buffered writers, counters); evaluates decisions using the shared registry.
  - Mission-scoped prevents cross-mission interference and reduces blast radius.

  ---

  ## 5. Trust model (chain of trust)

  ### 5.1 Trusted inputs (injected)
  - mission_id (string)
  - mission_type (string; immutable)
  - agent_tier (int; immutable)
  - attempt_count (int; loop-controlled)
  - tool/action (strings; tool wrapper controlled)

  ### 5.2 Untrusted inputs (must be validated/translated)
  - file paths and any tool arguments originating from agent requests
  - raw stderr/stdout, exceptions, exit codes (must be classified into failure_class)

  ### 5.3 Enforcement rule
  - PolicyContext is constructed only in orchestration adapters; agent payloads cannot set
  mission_type/agent_tier.
  - ContextFactory is used as a central constructor, but is not treated as a cryptographic boundary;
  the real boundary is adapter ownership.

  ---

  ## 6. Configuration model (schema-validated)

  ### 6.1 policy_rules.yaml (includes + global settings)
  - version: "1.2"
  - includes: tool_rules.yaml, loop_rules.yaml
  - audit settings
  - metrics settings
  - escalation settings
  - enforcement mode: SHADOW / DUAL / PRIMARY / ONLY (see §13)

  ### 6.2 variables.yaml (locked variables; absolute paths)
  - LIFEOS_SANDBOX_ROOT (absolute)
  - LIFEOS_ARTIFACTS (absolute)
  - LIFEOS_GOVERNANCE_PATH (absolute)
  - LIFEOS_TEST_PATH (absolute)
  - RESOLVER_ALLOWLIST (trusted resolver identities; minimal auth stub)
  - BOOTSTRAP_APPROVERS mapping (optional; see §9.5)

  ### 6.3 posture.yaml (policy-engine posture; CSO-aligned semantics)
  This file holds tunable operational defaults (not invariants). If missing, safe defaults apply.

  Safe defaults (used only if posture.yaml missing):
  - escalation budgets:
  - blocking_max_pending_per_mission: 2
  - observational_max_pending_per_mission: 10
  - default timeouts:
  - council_review: 3600
  - ceo_approval: 86400
  - cso_approval: 7200
  - audit buffer:
  - audit_buffer_max_records: 50
  - audit_flush_interval_seconds: 5
  - metrics buffer:
  - metrics_buffer_max_records: 200
  - metrics_flush_interval_seconds: 10
  - proxy decision TTL:
  - pd_ttl_cycles_default: 1

  Safe ranges (binding; out-of-range prohibited; triggers escalation):
  - blocking_max_pending_per_mission: 0..5
  - observational_max_pending_per_mission: 0..50
  - council_review_timeout_seconds: 60..14400
  - cso_approval_timeout_seconds: 60..28800
  - ceo_approval_timeout_seconds: 300..259200
  - audit_buffer_max_records: 1..1000
  - audit_flush_interval_seconds: 1..30
  - metrics_buffer_max_records: 1..5000
  - metrics_flush_interval_seconds: 1..60
  - pd_ttl_cycles_default: 0..3

  Loosening vs tightening (binding; posture governance):
  - Loosening includes: increasing timeouts, increasing budgets, reducing audit rigor, widening
  fallbacks from DENY/TERMINATE toward ALLOW/RETRY.
  - Any loosening requires CEO CDP outcome (recorded externally); engine must refuse to load a posture
  marked as “loosening-approved: false” when it detects loosening deltas.
  - Tightening is permitted with Standard logging.

  Implementation note (mechanisable): posture loader computes a delta classification vs the last known
  posture snapshot and emits an Escalation Notice artifact if loosening is detected without explicit
  approval marker.

  ### 6.4 failure_classes.yaml (required; schema-validated)
  - Must exist and validate at startup (no optional classifier config).
  - Includes:
  - default_class: "UNKNOWN"
  - rules (exception_type / exit_code / message_pattern)
  - fallback_strategy for UNKNOWN (see §10.3)

  ---

  ## 7. Rule types

  ### 7.1 Tool rules
  Decision: ALLOW | DENY | ESCALATE
  Conditions may include:
  - tool, action(s)
  - path_matches (glob, absolute canonical)
  - path_within (absolute canonical containment)
  - mission_type (trusted)
  - agent_tier (trusted)

  ### 7.2 Loop rules
  Decision: RETRY | TERMINATE | ESCALATE
  Conditions may include:
  - failure_class (classified)
  - attempt_count comparisons
  - mission_type, agent_tier (trusted)

  ### 7.3 Escalation metadata (mandatory for ESCALATE)
  - escalation.type: council_review | ceo_approval | cso_approval | ceo_notification
  - escalation.category: BLOCKING | OBSERVATIONAL
  - escalation.timeout_seconds (optional; defaults from posture)
  - escalation.fallback (tool: DENY; loop: TERMINATE unless overridden)
  - escalation.priority: critical | normal

  ---

  ## 8. Evaluation algorithm (deterministic, autonomy-safe)

  ### 8.1 Matching
  A rule matches if:
  - surface matches (tool vs loop)
  - required selectors match (tool/action for tool rules)
  - all specified conditions evaluate true
  - paths are canonicalized before evaluation (see §11)

  ### 8.2 Specificity scoring (v1.2 fixed; no “list length wins”)
  Specificity measures **constraint narrowness**, not breadth. Scoring uses presence + singleton
  bonuses only.

  Weights:
  - TOOL present: +10
  - ACTION constrained: +35
  - if exactly one action: +10 bonus
  - if <= 3 actions: +5 bonus
  - PATH_EXACT: +60
  - PATH_GLOB: +35
  - PATH_WITHIN: +25
  - MISSION_TYPE constrained: +25
  - if singleton mission_type: +10 bonus
  - AGENT_TIER constrained: +10
  - FAILURE_CLASS constrained: +30
  - ATTEMPT_COUNT constraint present: +20

  Guarantee (structural): TOOL+ACTION (single action) outranks MISSION_TYPE singleton.
  - Tool ban: 10 + 35 + 10 = 55
  - Mission allow: 25 + 10 = 35

  This eliminates the “global ban trap”: a mission allowance cannot bypass an explicit tool-action ban
  without adding brittle dummy conditions.

  ### 8.3 Selection and ties
  - Select highest specificity.
  - If tied: lexicographic rule_id ascending.
  - Tie with conflicting decisions is prohibited:
  - prefer load-time rejection where detectable; otherwise runtime raises PolicyConflictError
  (fail-closed).

  ### 8.4 Default outcome (fail-closed)
  - Tool surface: DENY if no match.
  - Loop surface: TERMINATE if no match.

  ---

  ## 9. Escalation system (end-to-end)

  ### 9.1 Escalation artifacts
  Directory: `${LIFEOS_ARTIFACTS}/escalations/`

  Files:
  - `pending/ESCALATION_ID.json`
  - `resolved/ESCALATION_ID.json`
  - `alerts/ESCALATION_ID.log` (optional, for CLI banner mirroring)

  Pending schema (minimum):
  - escalation_id
  - created_at (informational)
  - mission_id, mission_type, agent_tier
  - surface (tool|loop), tool/action or failure_class/attempt_count
  - proposed_decision, fallback, timeout_seconds, category, priority
  - matched_rule_id, rule_reason
  - canonical_path (if applicable)
  - required_resolver (ceo|cso|council|bootstrap)

  Resolved schema (minimum):
  - escalation_id
  - resolved_at (informational)
  - resolver_id (must be in RESOLVER_ALLOWLIST)
  - decision (ALLOW/DENY for tool; RETRY/TERMINATE for loop; or explicit OVERRIDE result)
  - reason (string; required)
  - valid_until (required for CSO/Council proxy approvals; see §9.4)
  - supersedes (optional; for revised decisions)

  ### 9.2 Notification modes
  - CLI banner: print “APPROVAL REQUIRED: ESCALATION_ID; run ‘lifeos governance
  pending/show/approve/deny’”
  - Artifact: creation of pending file is treated as notification for non-interactive workflows
  - Both is recommended

  ### 9.3 CLI commands (canonical interface)
  - `lifeos governance pending [--mission_id MISSION_ID]`
  - `lifeos governance show ESCALATION_ID`
  - `lifeos governance approve ESCALATION_ID --by RESOLVER_ID --reason "TEXT" [--valid_until ISO8601]`
  - `lifeos governance deny ESCALATION_ID --by RESOLVER_ID --reason "TEXT" [--valid_until ISO8601]`

  ### 9.4 Proxy validity / TTL (CSO-aligned)
  - If resolver_id is CSO or COUNCIL (proxy lane), `valid_until` is REQUIRED.
  - Default TTL if not provided is prohibited (fail-closed): the CLI must demand it or compute it
  deterministically from posture (pd_ttl_cycles_default) if posture provides cycle timing. v1.2
  chooses: CLI requires explicit valid_until to avoid hidden time semantics.
  - Any attempt to act on an expired proxy approval is prohibited; engine must treat it as unresolved
  and apply timeout/fallback.

  ### 9.5 Bootstrap mode (until full authority plumbing is automated)
  - `BOOTSTRAP_APPROVERS` maps escalation.type → required_resolver_id.
  - If bootstrap mode is used, engine writes a Bootstrap Notice artifact once per mission.
  - Bootstrap is allowed but explicit; it must not silently expand authority.

  ### 9.6 Throttling (autonomy-safe)
  Budgets are per mission and per category (from posture):
  - BLOCKING pending max (default 2)
  - OBSERVATIONAL pending max (default 10)

  Over-budget behavior:
  - BLOCKING: default FAIL_MISSION (hard stop; explicit failure artifact)
  - OBSERVATIONAL: AUTO_FALLBACK (apply fallback, log THROTTLED)

  Priority:
  - critical escalations are admitted before normal; if budget is full, normal escalations are
  throttled first.

  ---

  ## 10. Failure classification (mandatory; robust)

  ### 10.1 ResultClassifier contract
  Input: {tool_name, exit_code, exception_type, stdout_snippet, stderr_snippet}
  Output: failure_class (enum)

  ### 10.2 Startup requirements
  - failure_classes.yaml must exist and schema-validate.
  - classifier runs a small self-test: verifies that at least one rule exists and that default_class is
  valid.

  ### 10.3 UNKNOWN fallback strategy (prevents regex fragility paralysis)
  Because message_pattern regexes can drift (locale, tool version), UNKNOWN must not automatically
  hard-terminate without a controlled pathway.

  Fallback strategy:
  - If classification yields UNKNOWN:
  - map to RETRYABLE_UNKNOWN for up to N retries (N from failure_classes.yaml; default 2)
  - after N: ESCALATE (cso_approval by default) with fallback TERMINATE
  - Every UNKNOWN event increments a counter and emits a warning line in audit.

  This preserves fail-closed posture while avoiding “minor format change = immediate termination
  everywhere.”

  ---

  ## 11. Path validation (canonical, consistent)

  ### 11.1 Absolute-path contract (structural)
  All configured path variables (sandbox/governance/tests/artifacts) are absolute. All path
  matching/containment is performed on canonical absolute paths.

  ### 11.2 Canonicalization rules
  - Normalize path (collapse `..`, `.`, separators).
  - Resolve existing components without following symlinks into prohibited areas; if any existing
  component is a symlink: deny for protected operations.
  - Containment check is component-based (not naive prefix).

  ### 11.3 Policy conditions supported
  - path_within: containment check under root
  - path_matches: glob match under canonical absolute form

  ---

  ## 12. Audit + metrics (buffered; enforcement-aware)

  ### 12.1 Buffered audit writer (JSONL)
  - Buffer records in memory; flush on:
  - buffer size ≥ audit_buffer_max_records
  - time since last flush ≥ audit_flush_interval_seconds
  - process shutdown (atexit)
  - If write fails:
  - SHADOW/DUAL: continue evaluation; emit a critical audit-write-failure artifact
  - PRIMARY/ONLY: fail mission (fail-closed; evidence truth required)

  Each audit record includes:
  - audit_id (uuid), timestamp (informational)
  - mission_id, mission_type, agent_tier
  - context snapshot
  - matched_rule_id, specificity_score
  - decision, escalation metadata
  - canonical_path (if applicable)
  - classification details (loop surface)

  ### 12.2 Metrics
  - In-memory counters + latency histogram
  - Buffered JSONL flush on size/time/shutdown
  - Optional Prometheus exposition endpoint (local):
  - enforce cardinality caps with overflow buckets (rule_id_max, tool_action_pairs_max)

  Required metrics:
  - decisions_total{surface,decision}
  - rule_hits_total{rule_id|overflow}
  - escalations_total{type,category,status}
  - pending_escalations{category}
  - decision_latency_ms_bucket
  - classifier_unknown_total
  - audit_write_failures_total

  ---

  ## 13. Migration plan (objective gates; staged by risk surface)

  ### 13.1 Modes
  - SHADOW: engine evaluates/logs; hardcoded policy governs execution
  - DUAL: engine evaluates; mismatches fail tests (CI gate)
  - PRIMARY: engine governs selected surfaces (start read-only)
  - ONLY: engine governs all configured surfaces

  ### 13.2 Promotion gates (no calendar-only promotion)
  Promotion requires all:
  - mismatch_rate == 0 across N runs (N defined in migration config; default 20)
  - audit_write_failures == 0 across N runs (for promotion to PRIMARY/ONLY)
  - escalation backlog within budgets across N runs
  - p99 decision latency meets target under expected load

  ### 13.3 Staged activation order
  1) filesystem read/list
  2) git status/diff
  3) pytest run (tool)
  4) filesystem write (non-governance)
  5) governance write (blocking escalation; CEO lane)
  6) git push (blocking escalation; CEO lane)
  7) loop policy enforcement

  ---

  ## 14. Authority mapping (CSO v1.3.3 integration)

  ### 14.1 Strategic-by-default triggers (policy-engine surfaces)
  Policy rules that touch any of:
  - governance/protocol/constitution documents
  - evidence/audit truth constraints (including disabling audit writes in enforcing mode)
  - loosening posture thresholds (budgets/timeouts/fallback permissiveness)
  - external communications tool surfaces or recipient classes

  …must route to CEO approval (ceo_approval) and be treated as Strategic-by-default.

  ### 14.2 CSO lane (Standard/Routine within envelope)
  CSO approvals are permitted only when:
  - the action is reversible or bounded
  - it does not expand authority
  - it does not loosen posture without CEO approval
  - it includes required evidence and TTL (valid_until)

  Loop escalations for ambiguous classifications typically route to CSO first (cso_approval), unless
  they implicate Strategic triggers above.

  ### 14.3 Council lane
  Council review may be used as an input to CEO decisions, but v1.2 treats final authority for
  Strategic/Significant as CEO-only. If a council_review escalation is used, resolution must still be
  consistent with required_resolver mapping (bootstrap approvers) until council resolution is
  mechanised.

  ---

  ## 15. Recovery and degradation pathways (bounded)

  R1. Metrics failures:
  - Metrics writer failure degrades to in-memory counters; engine continues. A critical artifact is
  emitted.

  R2. Audit failures:
  - In SHADOW/DUAL: continue + emit critical artifact.
  - In PRIMARY/ONLY: fail mission (fail-closed).

  R3. Escalation state corruption (malformed pending/resolved file):
  - Treat as unresolved; emit quarantine artifact; apply timeout/fallback.

  R4. Classifier degradation:
  - UNKNOWN fallback strategy applies; if UNKNOWN rate breaches threshold (configurable), emit
  escalation to CSO.

  ---

  ## 16. Verification plan (tests required)

  ### 16.1 Unit tests
  - schema validation failures fail-closed
  - specificity scoring cases:
  - tool+action ban outranks mission allow
  - no list-length inversion
  - deterministic tie-breaking and conflict rejection
  - path canonicalization and containment correctness
  - escalation budgets and over-budget behaviors
  - resolver allowlist enforcement + TTL enforcement
  - classifier UNKNOWN fallback strategy behavior

  ### 16.2 Integration tests
  - end-to-end escalation:
  - create pending
  - approve/deny via CLI
  - decision applied
  - TTL expiry rejected
  - buffered audit/metrics flush triggers (size/time/shutdown)
  - concurrency: multiple evaluations do not corrupt buffers (thread safety)

  ### 16.3 Simulation tooling tests
  - `lifeos policy test-rule` deterministic outputs
  - `lifeos policy replay` produces stable report across runs

  ---

  ## 17. Deliverables (deterministic file list)

  Code:
  - runtime/governance/* modules listed in §4.1
  - runtime/orchestration/* adapters listed in §4.1
  Config:
  - config/policy/* files listed in §4.1 with schemas
  Tests:
  - runtime/tests/governance/test_policy_engine_unit.py
  - runtime/tests/governance/test_escalation_e2e.py
  - runtime/tests/governance/test_classifier.py
  - runtime/tests/governance/test_path_validator.py
  CLI:
  - `lifeos governance ...`
  - `lifeos policy test-rule ...`
  - `lifeos policy replay ...`

  ---

  ## 18. DONE definition (acceptance)

  Policy Engine v1.2 is DONE when:
  1) Engine loads only schema-valid config; invalid config fails closed.
  2) Tool and loop decisions are deterministic (outcome-stable) with fixed specificity math.
  3) End-to-end escalation works (pending/notify/resolve/TTL/budget/throttle).
  4) Failure classification is mandatory and robust to regex misses (UNKNOWN fallback strategy).
  5) Audit and metrics are buffered; no per-decision open/write/close thrash.
  6) Authority mapping enforces CSO v1.3.3 tiers:
  - Strategic/Significant surfaces route to CEO approval
  - CSO lane is bounded and time-limited
  - external comms remain hard-gated by CE
  7) Migration gates are objective; PRIMARY/ONLY promotion is blocked until gates pass.
  ```