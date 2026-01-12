# Intent Routing Rule v1.0
LifeOS Governance Hub — Routing Protocol
Status: Active
Applies To: COO Runtime, AI Council, CSO
Authority: Subordinate to LifeOS v1.1, CSO Charter v1.0, CEO Interaction Directive v1.0

============================================================
0. PURPOSE
============================================================
This protocol defines how all questions, decisions, ambiguities, and escalations are routed between:

- COO Runtime (execution)
- CSO (intent interpretation)
- AI Council (governance review)

It ensures:
- strict separation of execution vs interpretation
- correct handling of Category 1, 2, and 3 decisions
- clarity about what reaches the CEO
- alignment with the CSO Operating Model v1

============================================================
1. CLASSIFICATION MODEL
============================================================
Every issue must be classified by COO or CSO into:

### Category 1 — Technical / Operational
Examples:
- runtime mechanics
- determinism checks
- file/dir layout
- council prompt mechanics
- build sequencing

**Rule:**
COO resolves internally.  
Never escalated to CEO.  
Council used only if correctness requires it.

### Category 2 — Structural / Governance / Safety
Examples:
- invariants
- governance leakage
- architectural forks
- determinism hazards
- ambiguity requiring governance interpretation

**Rule:**
COO → Council (for analysis)
Council → COO (synthesised findings)
COO → CSO (single synthesised question)
CSO → CEO (only if CEO decision needed)

### Category 3 — Strategic / Preference / Intent
Examples:
- long-term direction
- priorities
- autonomy expansion
- productisation shifts
- decisions with multiple viable paths

**Rule:**
Route directly to CSO.  
CSO frames the issue and prepares the CEO Decision Packet.

============================================================
2. COO → CSO ROUTING RULES
============================================================

COO MUST route an issue upward to CSO when:

1. A mission depends on CEO preferences or strategic choice.
2. Ambiguity remains after COO and Council analysis.
3. A Category 3 classification is made.
4. Council recommends CEO arbitration.
5. Operational work is blocked by missing intent.
6. System behaviour may contradict the CEO’s stated trajectory.

COO MUST NOT route to CEO directly under any circumstances.

COO MUST synthesise all Council output before passing to CSO.

============================================================
3. CSO → COO ROUTING RULES
============================================================

CSO routes downward to COO when:

1. The decision is Category 1 (technical/operational).
2. The decision is Category 2 but resolvable without CEO input.
3. The CEO has already expressed stable preferences.
4. The issue is frictional, administrative, or would create “crank-turning”.
5. It requires execution, not interpretation.

CSO MUST NOT give operational instructions.  
CSO provides strategic briefs; COO handles execution.

============================================================
4. CSO → COUNCIL REQUESTS
============================================================

CSO may request Council involvement when:

1. A strategic mission contains structural or constitutional ambiguity.
2. A governance invariant may be implicated.
3. A risk requires multi-lens analysis.
4. Determinism or architecture questions exceed COO authority.

COO MUST:
- authorise
- configure
- invoke
- budget
- supervise

Council operations.

CSO cannot invoke the Council directly.

============================================================
5. WHAT MUST ALWAYS BE SURFACED TO CEO
============================================================
(Per CSO Operating Model v1 and the CEO Interaction Directive)

- Intent drift or long-term direction issues  
- Architectural/governance structure changes  
- Any autonomy expansion proposal  
- Any personal risk event  
- Major productisation pivots  
- Decisions with multiple viable strategic paths  

All must be surfaced via CSO in a CEO Decision Packet.

============================================================
6. WHAT MUST NEVER BE SURFACED TO CEO
============================================================

- Raw technical detail  
- Reviewer chatter  
- Multiple unresolved questions  
- Operational sequencing  
- Runtime mechanics  
- Build/process noise  
- Raw Council output  
- Any detail not framed in CEO-impact terms  

============================================================
7. DEFAULT RULE
============================================================

If COO or CSO are unsure how to route:

1. Route to CSO.  
2. CSO classifies Category 1, 2, or 3.  
3. COO and Council operate accordingly.  

No direct-to-CEO routing is permitted.

============================================================
END — Intent Routing Rule v1.0
============================================================

