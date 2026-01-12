# Artifacts Index

**Last Updated**: 2026-01-05

## Schema Reference

All artifacts **MUST** conform to the **Build Artifact Protocol v1.0**:

| Resource | Path |
|----------|------|
| Protocol | [`Build_Artifact_Protocol_v1.0.md`](file:///c:/Users/cabra/Projects/LifeOS/docs/02_protocols/Build_Artifact_Protocol_v1.0.md) |
| Schemas | [`build_artifact_schemas_v1.yaml`](file:///c:/Users/cabra/Projects/LifeOS/docs/02_protocols/build_artifact_schemas_v1.yaml) |
| Templates | [`templates/`](file:///c:/Users/cabra/Projects/LifeOS/docs/02_protocols/templates/) |

> [!IMPORTANT]
> All new artifacts must include YAML frontmatter per schema. See templates for examples.

## Directory Structure

| Folder | Purpose | Naming Convention |
|--------|---------|-------------------|
| `plans/` | Implementation plans, architecture plans | `Plan_<Topic>_v<X.Y>.md` |
| `review_packets/` | Completed work for CEO review | `Review_Packet_<Mission>_v<X.Y>.md` |
| `walkthroughs/` | Post-verification summaries | `Walkthrough_<Topic>_v<X.Y>.md` |
| `gap_analyses/` | Gap analysis artifacts | `GapAnalysis_<Scope>_v<X.Y>.md` |
| `doc_drafts/` | Documentation drafts pending review | `DocDraft_<Topic>_v<X.Y>.md` |
| `test_drafts/` | Test specification drafts | `TestDraft_<Module>_v<X.Y>.md` |
| `context_packs/` | Agent-to-agent handoff context | `ContextPack_<Type>_<UUID>.yaml` |
| `bundles/` | Zipped multi-file handoffs | `Bundle_<Topic>_<Date>.zip` |
| `missions/` | Mission telemetry logs | `<Date>_<Type>_<UUID>.yaml` |
| `packets/` | Structured YAML packets (inter-agent) | Per packet schema naming |
| `for_ceo/` | **CEO pickup folder** — files requiring CEO action | Copies of originals |

## Protocol

1. All artifacts MUST use proper naming per convention
2. All artifacts MUST include YAML frontmatter with `artifact_id`, `artifact_type`, `version`, etc.
3. Files requiring CEO action MUST be copied to `for_ceo/`
4. CEO clears `for_ceo/` after pickup

## Templates

| Artifact Type | Template |
|---------------|----------|
| Plan | [`plan_template.md`](file:///c:/Users/cabra/Projects/LifeOS/docs/02_protocols/templates/plan_template.md) |
| Review Packet | [`review_packet_template.md`](file:///c:/Users/cabra/Projects/LifeOS/docs/02_protocols/templates/review_packet_template.md) |
| Walkthrough | [`walkthrough_template.md`](file:///c:/Users/cabra/Projects/LifeOS/docs/02_protocols/templates/walkthrough_template.md) |
| Gap Analysis | [`gap_analysis_template.md`](file:///c:/Users/cabra/Projects/LifeOS/docs/02_protocols/templates/gap_analysis_template.md) |
| Doc Draft | [`doc_draft_template.md`](file:///c:/Users/cabra/Projects/LifeOS/docs/02_protocols/templates/doc_draft_template.md) |
| Test Draft | [`test_draft_template.md`](file:///c:/Users/cabra/Projects/LifeOS/docs/02_protocols/templates/test_draft_template.md) |
