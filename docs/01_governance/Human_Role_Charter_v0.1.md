# LifeOS — Human Role Charter v0.1

**Status**: Active
**Parent**: Anti-Failure Operational Packet v0.1
**Purpose**: Protect the human from burnout by strictly limiting their operational footprint.

## 1. Core Principle: Human Preservation
The human is a **fragile node**. They are:
- High-value (Intent/Creativity)
- Low-reliability (Availability/Energy)
- Non-scalable

Therefore, the human **must not** be on the critical path for routine operations.

## 2. Permitted Human Actions (The "White List")

The human may ONLY perform the following:

1.  **Define Intent**: "Build a website", "Fix this bug".
2.  **Approve / Veto**: "Looks good", "Stop, that's wrong".
3.  **Governance**: "Update the Constitution", "Key decision on architecture".
4.  **Edge Case Resolution**: "The plan failed, here is the new direction".
5.  **Review**: Reading summaries and artifacts.

## 3. Prohibited Human Actions (The "Black List")

The human MUST NOT:

1.  **Crank-Turning**: Manually running a series of commands daily.
2.  **Manual Indexing**: Updating lists of files by hand.
3.  **Formatting**: Fixing markdown whitespace or linting.
4.  **Copy-Pasting**: Moving content between files manually.
5.  **Memory Storage**: Keeping track of "what needs to be done next" (Use `task.md` or backlog).

## 4. Enforcement

- **Agent Responsibility**: If an agent sees the human doing a "Black List" item, it must propose an automation fix appropriately.
- **Human Responsibility**: The human has the right to refuse work that violates this charter.
