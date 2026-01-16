# Artifact Formalization Protocol — Implementation Plan

| Field | Value |
|-------|-------|
| **Version** | 0.1 |
| **Date** | 2026-01-05 |
| **Author** | Antigravity |
| **Status** | DRAFT — Awaiting CEO Review |
| **Council Trigger** | CT-2 (New Protocol) |

---

## Executive Summary

Formalize versioned schemas and templates for all build artifacts (Plans, Review Packets, Walkthroughs, Gap Analyses) to enable deterministic, machine-parseable outputs for future OpenCode automation. This creates the **Build Artifact Protocol v1.0** — a companion to the existing Agent Packet Protocol for YAML inter-agent packets.

---

## Problem Statement

**Current State:**
- YAML packets (inter-agent communication) have formal schemas in `lifeos_packet_schemas_v1.yaml`
- Markdown artifacts (plans, review packets, walkthroughs) have informal conventions in `GEMINI.md`
- No formal schema definitions, templates, or validation rules for markdown artifacts
- Inconsistent structure across existing artifacts

**Impact:**
- OpenCode agents cannot reliably produce/parse artifacts
- Human review burden (no structural consistency)
- No machine validation possible
- Future automation blocked

---

## Proposed Solution

Create **Build Artifact Protocol v1.0** with:

1. **Formal Schema Definitions** — YAML schema file defining required/optional sections
2. **Markdown Templates** — Ready-to-use templates for each artifact type
3. **Canonical Directories** — Formalized folder structure (consolidating current `artifacts/` layout)
4. **Validation Guidance** — Machine-checkable requirements
5. **Protocol Integration** — Reference from GEMINI.md and Document Steward Protocol

---

## User Review Required

> [!IMPORTANT]
> This plan creates a new protocol (`Build_Artifact_Protocol_v1.0.md`) that formalizes artifact production. Per CT-2, this requires Council review before activation.

### Key Decisions Needed

1. **Retroactive compliance?** Should existing artifacts be migrated to new format, or only new artifacts?
2. **YAML metadata headers?** Should markdown artifacts include a YAML frontmatter block for machine parsing?
3. **Strictness level?** Should validation be WARN (non-blocking) or FAIL (blocking)?

---

## Proposed Changes

### Component 1: Protocol Definition

#### [NEW] [Build_Artifact_Protocol_v1.0.md](file:///c:/Users/cabra/Projects/LifeOS/docs/02_protocols/Build_Artifact_Protocol_v1.0.md)

Formal protocol defining:

- **6 Artifact Types**: Plan, Review Packet, Walkthrough, Gap Analysis, Doc Draft, Test Draft
- **Mandatory Metadata Block** for each (YAML frontmatter)
- **Required Sections** per artifact type
- **Naming Conventions** (already partially defined in GEMINI.md)
- **Validation Rules**

---

### Component 2: Schema Definitions

#### [NEW] [build_artifact_schemas_v1.yaml](file:///c:/Users/cabra/Projects/LifeOS/docs/02_protocols/build_artifact_schemas_v1.yaml)

Machine-readable schema file defining:

```yaml
# Build Artifact Schemas v1.0
# Companion to lifeos_packet_schemas_v1.yaml for markdown artifacts

_common_metadata:
  # Required YAML frontmatter for ALL artifacts
  artifact_id: string        # UUID v4
  artifact_type: string      # PLAN | REVIEW_PACKET | WALKTHROUGH | GAP_ANALYSIS | DOC_DRAFT | TEST_DRAFT
  schema_version: string     # Semver e.g., "1.0.0"
  created_at: datetime       # ISO 8601
  author: string             # "Antigravity" or agent identifier
  version: string            # Artifact version e.g., "0.1"
  status: string             # DRAFT | PENDING_REVIEW | APPROVED | SUPERSEDED
  
  # Optional
  chain_id: string           # Links to packet chain if part of workflow
  mission_ref: string        # Mission this artifact belongs to
  council_trigger: string    # CT-1 through CT-5 if applicable
  parent_artifact: string    # Path to artifact this supersedes

plan_artifact_schema:
  artifact_type: "PLAN"
  required_sections:
    - executive_summary       # 2-5 sentence overview
    - problem_statement       # What problem this solves
    - proposed_changes        # Detailed change list
    - verification_plan       # How changes will be verified
  optional_sections:
    - user_review_required    # Decisions needing CEO input
    - alternatives_considered # Other approaches evaluated
    - rollback_plan           # How to undo if failed
    - success_criteria        # Measurable outcomes
    - non_goals               # Explicit exclusions
  naming: "Plan_<Topic>_v<X.Y>.md"
  canonical_path: "artifacts/plans/"

review_packet_schema:
  artifact_type: "REVIEW_PACKET"
  required_sections:
    - executive_summary       # Mission outcome summary
    - issue_catalogue         # Table of issues/resolutions
    - acceptance_criteria     # Pass/fail status table
    - stewardship_evidence    # Proof of doc stewardship (if applicable)
    - verification_proof      # Test results, command outputs
    - flattened_code_appendix # All created/modified files
  optional_sections:
    - constraints_boundaries  # Runtime limits if applicable
    - non_goals               # Explicit out-of-scope
  naming: "Review_Packet_<Mission>_v<X.Y>.md"
  canonical_path: "artifacts/review_packets/"

walkthrough_schema:
  artifact_type: "WALKTHROUGH"
  required_sections:
    - summary                 # What was accomplished
    - changes_made            # List of changes with rationale
    - verification_results    # What was tested and outcomes
  optional_sections:
    - screenshots             # Embedded visual evidence
    - recordings              # Paths to browser recording files
    - known_issues            # Issues discovered but not fixed
    - next_steps              # Follow-up work suggested
  naming: "Walkthrough_<Topic>_v<X.Y>.md"
  canonical_path: "artifacts/walkthroughs/"

gap_analysis_schema:
  artifact_type: "GAP_ANALYSIS"
  required_sections:
    - scope                   # What was scanned
    - findings                # Table of gaps with severity
    - remediation_recommendations  # Proposed fixes
  optional_sections:
    - methodology             # How analysis was performed
    - priority_matrix         # Critical vs informational
  naming: "GapAnalysis_<Scope>_v<X.Y>.md"
  canonical_path: "artifacts/gap_analyses/"

doc_draft_schema:
  artifact_type: "DOC_DRAFT"
  required_sections:
    - target_document         # Path to document being drafted
    - change_type             # ADDITIVE | MODIFYING | REPLACING
    - draft_content           # The actual content
    - dependencies            # What this depends on
  naming: "DocDraft_<Topic>_v<X.Y>.md"
  canonical_path: "artifacts/doc_drafts/"

test_draft_schema:
  artifact_type: "TEST_DRAFT"
  required_sections:
    - target_modules          # What's being tested
    - test_cases              # Detailed test specifications
    - coverage_targets        # What coverage is expected
  optional_sections:
    - edge_cases              # Boundary condition tests
    - integration_points      # Cross-module test needs
  naming: "TestDraft_<Module>_v<X.Y>.md"
  canonical_path: "artifacts/test_drafts/"
```

---

### Component 3: Templates

#### [NEW] [build_artifact_templates_v1/](file:///c:/Users/cabra/Projects/LifeOS/docs/02_protocols/templates/)

Directory containing ready-to-use templates:

| Template | Purpose |
|----------|---------|
| `plan_template.md` | Implementation/architecture plan |
| `review_packet_template.md` | Mission completion review |
| `walkthrough_template.md` | Post-verification summary |
| `gap_analysis_template.md` | Gap/inconsistency analysis |
| `doc_draft_template.md` | Documentation draft |
| `test_draft_template.md` | Test specification draft |

Each template includes:
- YAML frontmatter with placeholders
- Required sections with guidance comments
- Optional sections marked as such
- Example content where helpful

**Example: `plan_template.md`**

```markdown
---
artifact_id: ""              # [REQUIRED] Generate UUID v4
artifact_type: "PLAN"
schema_version: "1.0.0"
created_at: ""               # [REQUIRED] ISO 8601
author: "Antigravity"
version: "0.1"
status: "DRAFT"
mission_ref: ""
council_trigger: ""          # CT-1 through CT-5 if applicable
---

# <Topic> — Implementation Plan

| Field | Value |
|-------|-------|
| **Version** | 0.1 |
| **Date** | YYYY-MM-DD |
| **Author** | Antigravity |
| **Status** | DRAFT — Awaiting CEO Review |
| **Council Trigger** | <!-- CT-1..CT-5 or "None" --> |

---

## Executive Summary

<!-- 2-5 sentences summarizing the goal and approach -->

---

## Problem Statement

<!-- What problem does this solve? Why is it important? -->

---

## Proposed Changes

### Component 1: <Name>

#### [MODIFY|NEW|DELETE] [filename](file:///path/to/file)

<!-- Description of changes -->

---

## Verification Plan

### Automated Tests
<!-- Commands to run, expected outcomes -->

### Manual Verification
<!-- CEO/human verification steps -->

---

<!-- OPTIONAL SECTIONS BELOW -->

## User Review Required

> [!IMPORTANT]
> <!-- Key decisions requiring CEO input -->

---

## Alternatives Considered

<!-- Other approaches and why rejected -->

---

## Rollback Plan

<!-- How to undo changes if failed -->

---

## Success Criteria

<!-- Measurable outcomes -->

---

## Non-Goals

<!-- Explicit exclusions from this plan -->

---

*This plan was drafted by Antigravity under LifeOS Build Artifact Protocol v1.0.*
```

---

### Component 4: Directory Structure Update

#### [MODIFY] [artifacts/INDEX.md](file:///c:/Users/cabra/Projects/LifeOS/artifacts/INDEX.md)

Add schema/template references and formalize directory structure:

```diff
 # Artifacts Index
 
-**Last Updated**: 2026-01-04
+**Last Updated**: 2026-01-05
+
+## Schema Reference
+
+All artifacts MUST conform to the **Build Artifact Protocol v1.0**:
+
+| Resource | Path |
+|----------|------|
+| Protocol | `docs/02_protocols/Build_Artifact_Protocol_v1.0.md` |
+| Schemas | `docs/02_protocols/build_artifact_schemas_v1.yaml` |
+| Templates | `docs/02_protocols/templates/` |
 
 ## Directory Structure
 
 | Folder | Purpose | Naming Convention |
 |--------|---------|-------------------|
 | `plans/` | Implementation plans, architecture plans | `Plan_<Topic>_v<X.Y>.md` |
 | `review_packets/` | Completed work for CEO review | `Review_Packet_<Mission>_v<X.Y>.md` |
+| `walkthroughs/` | Post-verification summaries | `Walkthrough_<Topic>_v<X.Y>.md` |
+| `doc_drafts/` | Documentation drafts pending review | `DocDraft_<Topic>_v<X.Y>.md` |
+| `test_drafts/` | Test specification drafts | `TestDraft_<Module>_v<X.Y>.md` |
 | `context_packs/` | Agent-to-agent handoff context | `ContextPack_<Type>_<UUID>.yaml` |
 | `bundles/` | Zipped multi-file handoffs | `Bundle_<Topic>_<Date>.zip` |
 | `missions/` | Mission telemetry logs | `<Date>_<Type>_<UUID>.yaml` |
 | `packets/` | Structured YAML packets (inter-agent) | Per packet schema naming |
 | `gap_analyses/` | Gap analysis artifacts | `GapAnalysis_<Scope>_v<X.Y>.md` |
 | `for_ceo/` | **CEO pickup folder** — files requiring CEO action | Copies of originals |
```

---

### Component 5: GEMINI.md Update

#### [MODIFY] [GEMINI.md](file:///c:/Users/cabra/Projects/LifeOS/GEMINI.md)

Add reference to new protocol in Appendix A:

```diff
 # APPENDIX A — NAMING & FILE CONVENTIONS
 
 1. Naming must follow repo conventions.
 2. Governance/spec files must use version suffixes.
-3. Artefacts use patterns:
-   - `Plan_<Topic>_vX.Y.md`
-   - `Diff_<Target>_vX.Y.md`
-   - `DocDraft_<Topic>_vX.Y.md`
-   - `TestDraft_<Module>_vX.Y.md`
-   - `GapAnalysis_<Scope>_vX.Y.md`
+3. Artefacts MUST conform to **Build Artifact Protocol v1.0**:
+   - Schema: `docs/02_protocols/build_artifact_schemas_v1.yaml`
+   - Templates: `docs/02_protocols/templates/`
+   - All artifacts MUST include YAML frontmatter per schema
+   - Naming patterns:
+     - `Plan_<Topic>_vX.Y.md`
+     - `Review_Packet_<Mission>_vX.Y.md`
+     - `Walkthrough_<Topic>_vX.Y.md`
+     - `DocDraft_<Topic>_vX.Y.md`
+     - `TestDraft_<Module>_vX.Y.md`
+     - `GapAnalysis_<Scope>_vX.Y.md`
 4. Artefacts must contain full metadata and rationale.
 5. Index files must not be directly edited.
 6. Repo-local `GEMINI.md` must be copied from this template.
```

---

## Verification Plan

### Automated Tests

| Test | Command | Expected |
|------|---------|----------|
| Schema YAML valid | `python -c "import yaml; yaml.safe_load(open('docs/02_protocols/build_artifact_schemas_v1.yaml'))"` | No errors |
| Templates exist | `ls docs/02_protocols/templates/*.md` | 6 files |
| Frontmatter parseable | `python scripts/validate_artifact.py artifacts/plans/Plan_*.md` | VALID |

### Manual Verification

1. Create a test Plan using new template
2. Verify YAML frontmatter parses correctly
3. CEO review of protocol document for completeness

---

## Deliverables Summary

| Deliverable | Path | Description |
|-------------|------|-------------|
| Protocol Definition | `docs/02_protocols/Build_Artifact_Protocol_v1.0.md` | Formal protocol document |
| Schema File | `docs/02_protocols/build_artifact_schemas_v1.yaml` | Machine-readable schemas |
| Plan Template | `docs/02_protocols/templates/plan_template.md` | Ready-to-use template |
| Review Packet Template | `docs/02_protocols/templates/review_packet_template.md` | Ready-to-use template |
| Walkthrough Template | `docs/02_protocols/templates/walkthrough_template.md` | Ready-to-use template |
| Gap Analysis Template | `docs/02_protocols/templates/gap_analysis_template.md` | Ready-to-use template |
| Doc Draft Template | `docs/02_protocols/templates/doc_draft_template.md` | Ready-to-use template |
| Test Draft Template | `docs/02_protocols/templates/test_draft_template.md` | Ready-to-use template |

---

## Migration Strategy

> [!NOTE]
> Existing artifacts will NOT be retroactively modified. New artifacts starting from approval will use the new format.

1. **Phase 1 (Immediate)**: New artifacts use new templates
2. **Phase 2 (Optional)**: High-frequency artifacts (plans, review packets) migrated opportunistically
3. **Phase 3 (Future)**: Validation tooling added to CI/pre-commit

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| Protocol document complete | CEO-approved after Council review |
| Templates usable | Agent produces valid artifact using template |
| Machine parseable | YAML frontmatter extracted by script |
| Integrated in GEMINI.md | New agents reference protocol |

---

## Non-Goals

- Retroactive migration of existing artifacts
- Automated validation tooling (deferred to future sprint)
- Changes to YAML packet schemas (separate protocol)
- Breaking changes to existing GEMINI.md structure

---

*This plan was drafted by Antigravity under LifeOS DAP v2.0 governance.*
