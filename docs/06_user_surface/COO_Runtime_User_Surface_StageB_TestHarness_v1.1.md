ANTIGRAVITY INSTRUCTION PACKET

COO Runtime V1.1 — User Surface Implementation (Stage B + Test Harness)

0. Authority & Scope

Authority chain (must not be violated):

LifeOS v1.1

Alignment Layer v1.4

COO Runtime Spec v1.0

Implementation Packet v1.0

R6.x Fix Packs (determinism, AMU₀, replay, rollback, crypto shim, proof-of-life)

Scope of this packet:

Implement the V1.1 User Surface in the existing coo-agent / CLI layer.

No changes to:

Runtime invariants

FSM semantics

Key-management model

Governance or QUESTION routing

DB schema (unless a pre-existing mission/log schema is already in place and sufficient)

Only:

Add a demo mission descriptor.

Add / extend CLI commands:

coo run-demo

coo mission <id>

coo logs <id>

Add a small internal product test suite.

You must use existing runtime APIs and abstractions wherever possible.

1. Project Assumptions (Do Not Fight Them)

There is an existing Python project coo-agent with:

A coo CLI entrypoint (Click/Typer/argparse or similar).

A runtime client or service module that:

Creates missions.

Executes missions.

Reads missions and logs from the DB.

Missions and logs are persisted in SQLite (or equivalent) as per the Implementation Packet.

There is already at least one reference mission descriptor (e.g. phase3_reference_mission.json); copy its structural patterns.

LLM calls are made through a central LLM client abstraction that:

Uses OpenRouter via OPENROUTER_API_KEY in .env.

Accepts a model name from config (COO_LLM_MODEL or a default constant).

If any of these assumptions are wrong, adapt minimally, but keep the intent: thin CLI layer, no new runtime capability.

2. Demo Mission Descriptor: DEMO_V1_1
2.1 File

Create a new mission descriptor:

Path (relative to repo root):
reference/demo_mission.json
(or the equivalent reference/mission directory used already – follow existing patterns)

2.2 Structure

Copy the schema from the smallest existing mission descriptor (e.g. phase3_reference_mission.json).

Set:

mission_type: "DEMO_V1_1"

A single task / step that performs:

One LLM call via the existing LLM client.

Deterministic post-processing only (string formatting).

Input text:

A short, fixed paragraph (~100–200 words) describing a simple system (e.g., a small AI service).

This text must be embedded in the descriptor or referenced in a fixed way so that it is identical across runs.

LLM prompt semantics:

Task: “Summarise the following description in 1–2 short paragraphs for a technical audience.”

No user input, no dynamic parameters.

2.3 Determinism

Enforce via descriptor / runtime integration:

Deterministic LLM settings:

temperature = 0

top_p = 1

Fixed max_tokens (256 or 512; choose a safe constant).

No tools / function-calling.

No randomness in post-processing.

3. LLM Resolution for the Demo

Do not create a new HTTP client for OpenRouter.

Use the existing LLM client abstraction used by other runtime tasks.

Resolution rule:

If COO_LLM_MODEL is set in .env, use that as the model string.

Otherwise, use the default model configured in the LLM client.

If neither exists, fail fast with a clear error:

ERROR: No model configured for LLM operations. Set COO_LLM_MODEL or configure a default model.


For the demo mission call:

Force deterministic parameters (temperature/top_p/max_tokens) in the call; do not rely on external defaults.

4. coo run-demo Implementation
4.1 CLI Surface

Add a subcommand to the existing coo CLI:

Command: coo run-demo

No options in V1.1.

If any options are supplied, print:

ERROR: 'coo run-demo' does not accept options in V1.1.


and exit with status 1.

4.2 Behaviour

Pseudocode-level flow:

Load demo_mission.json from the reference directory.

Create a mission in the runtime with:

mission_type = "DEMO_V1_1".

Execute mission via the existing mission execution API (whatever function currently drives INIT → COMPLETE).

Wait until execution completes (SUCCESS or FAILED).

Extract from the mission/logs:

Mission ID (string).

Mission status.

Started / finished timestamps.

Number of steps (state transitions).

Number of rollbacks.

Number of divergences (if tracked; otherwise, treat as 0).

The AI output string (summary text).

Format and print the Execution Receipt as below.

Write the same Receipt content to:

demo/<mission_id>/demo_report.txt

Under the runtime’s data/output directory; if you have a global data root, use it as prefix.

Ensure the directory is created if missing.

Exit code:

0 if mission status is SUCCESS.

1 if mission status is FAILED or any error happens after mission creation.

4.3 Output Format (Exact Sections, Flexible Spacing)

All output sections must appear in this order with these headings:

Prefix line:

[coo] Running deterministic demo mission ...


Mission block:

Mission
  ID: DEMO-<NNNNNN>
  Type: DEMO_V1_1
  Status: SUCCESS|FAILED
  Started: <timestamp>
  Finished: <timestamp>
  Steps: <N> transitions, <R> rollbacks, <D> divergences


Mission ID must be rendered as DEMO- + a zero-padded integer or similar.

If your DB uses an integer primary key, map it deterministically to this format.

AI Output block:

AI Output
  <the LLM-generated summary, wrapped to lines as appropriate>


Determinism block:

Determinism
  This result is reproducible on this machine.
  Re-running 'coo run-demo' with the same setup will produce the same output.
  The runtime captured a sealed internal snapshot and log for this run.


Inspect block:

Inspect
  coo mission DEMO-<NNNNNN>
  coo logs DEMO-<NNNNNN>


Minor whitespace differences are acceptable; headings and key sentences should match.

5. coo mission <id> Implementation
5.1 CLI Surface

Add or adapt:

coo mission <id>

Where <id> is the mission ID string, e.g. DEMO-000123 or other mission IDs.

5.2 Behaviour

Map <id> back to the internal mission identifier used in the DB.

For demo missions, convert DEMO-000123 to the underlying numeric ID or equivalent.

For non-demo missions, assume existing format or treat <id> as raw key if already used.

Query mission row from the DB.

Query associated state transition records ordered by sequence ID.

5.3 Output format

On success:

Mission <id>
  Type: <mission_type>
  Status: <status>
  Created: <timestamp>
  Started: <timestamp>
  Finished: <timestamp>

Timeline
  #0001 INIT
  #0002 CAPTURE_ENV
  #0003 RUN
  #0004 WRITE_REPORT
  #0005 COMPLETE


Important:

Use the actual state names from the FSM.

The Timeline lines should be numbered #NNNN in ascending sequence.

On failure to find:

ERROR: Mission '<id>' not found.


Exit code:

0 on success.

1 if not found or DB error.

6. coo logs <id> Implementation
6.1 CLI Surface

Add or adapt:

coo logs <id>

6.2 Behaviour

Resolve <id> as in coo mission.

Fetch all log entries for that mission in sequence order.

Print each entry as a single line:

[0001] STATE=<STATE_NAME> <rest_of_log_info>


Sequence number zero-padded to 4 digits.

STATE= prefix must be present.

<rest_of_log_info> should contain the most important fields the runtime already logs (but you do not need to invent new ones).

On missing mission/logs:

ERROR: Mission '<id>' not found.


Exit code:

0 on success.

1 if mission not found or DB error.

7. Internal Product Test Suite

Create a test module hierarchy for product-level behaviour tests:

Suggested layout:

tests/product/
  test_demo_repeatability.py
  test_demo_receipt_format.py
  test_mission_view.py
  test_logs_view.py
  test_demo_error_paths.py

7.1 test_demo_repeatability.py

Arrange:

Run coo run-demo twice in a fresh test environment (can be via CLI invocation or direct function calls).

Assert:

Both runs exit with code 0.

AI Output sections are identical strings.

Receipt sections (minus timestamps and mission ID) are identical.

7.2 test_demo_receipt_format.py

Run coo run-demo once.

Assert:

Output contains the 4 headings in order:

Mission

AI Output

Determinism

Inspect

The Determinism section contains the sentence:

"This result is reproducible on this machine."

7.3 test_mission_view.py

After a successful demo run, capture the mission ID.

Call coo mission <id> (or underlying function).

Assert:

Output includes Mission <id> line.

Timeline section exists.

At least one state line starts with #0001.

7.4 test_logs_view.py

After a successful demo run, call coo logs <id>.

Assert:

At least one line begins with [0001] STATE=.

Lines are sorted by sequence number.

7.5 test_demo_error_paths.py

Create tests that simulate:

No mission with given ID → coo mission invalid-id:

Expect ERROR: Mission 'invalid-id' not found. and exit code 1.

No mission with given ID → coo logs invalid-id:

Same pattern.

Misuse of coo run-demo with parameters:

coo run-demo --foo

Expect error message:

ERROR: 'coo run-demo' does not accept options in V1.1.

8. Non-Goals / Red Lines for This Packet

Do not:

Add new runtime states or transitions.

Modify core determinism logic.

Introduce new key formats or crypto schemes.

Implement Stage C flags (--contrast, --drift-check, etc.) yet.

Add network calls beyond the existing LLM client.

Do not:

Hardcode a specific model name in demo logic.

Create a separate LLM client for the demo.

Demo is strictly a thin orchestration + formatting layer over the existing runtime.