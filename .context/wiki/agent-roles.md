---
source_docs:
  - docs/00_foundations/Agent_Roles_Reference_v1.0.md
  - docs/00_foundations/LifeOS_Constitution_v2.0.md
  - docs/02_protocols/Intent_Routing_Rule_v1.1.md
  - docs/00_foundations/LifeOS Target Architecture v2.3c.md
source_commit_max: 4e8237cba053b2cb10dba7467f463286d1711fd7
authority: derived
page_class: evergreen
concepts:
  - COO
  - CEO
  - EA
  - COO substrates
  - CSO
  - autonomy levels
  - provider routing
  - delegation tiers

Two changes from the previous version:

1. **CEO row** — added explicit note that CEO authority is expressed via COO execution, never by direct state mutation. This reflects the v2.3c clarification in §4.3: *"The CEO never writes directly to canonical state surfaces… authority is real and supreme; its expression is via COO execution, not direct mutation."*

2. **EA row** — added "evidence producers, not state mutators" to align with v2.3c §2.4 which now explicitly states EAs do not modify the structured state block.
