---
description: Generate a structured handoff summary for another agent, or process an inbound handoff. Use when finishing a sprint, review, or build cycle that another agent will continue.
---

Invoke the lifeos-workflow:handoff skill and follow it exactly as presented to you.

If the user says "handoff" without direction, assume outbound (you are handing off your completed work). If the user provides another agent's output, process it as inbound.

Output must use compact sections in this order:
1. Branch
2. Commits
3. Test Results
4. What Was Done
5. What Remains
