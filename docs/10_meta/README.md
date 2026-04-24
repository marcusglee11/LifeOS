# Meta Documentation

Repository-level metadata, review packets, deprecation notices, historical records, and architecture-control surfaces.

## Contents

This directory contains meta-documentation about the LifeOS repository itself, including:

- **Code review status and packets**: Historical review artifacts
- **Deprecation notices**: Component sunset announcements
- **Implementation plans**: Meta-level planning documents
- **Governance digests**: Summaries of governance activity
- **Technical architecture signoffs**: Historical architecture approvals
- **Architecture control surfaces**: Source-of-truth map, changelog, decision register, reconciliation packets

## Active Files

- CHANGELOG.md - Legacy repository change log (stale; retained as historical surface)
- ARCHITECTURE_CHANGELOG.md - Architecture delta log
- ARCHITECTURE_SOURCE_OF_TRUTH.md - Current canon / proposal / stale map
- Architecture_Normalization_Reconciliation_Packet_2026-04-24.md - Normalization packet for canon, authority, writer boundaries, and mismatches
- COO_Authority_Contract_Draft_2026-04-24.md - Draft authority-boundary decisions for normalization
- architecture_decisions/INDEX.md - ADR register skeleton
- Architecture_Normalization_Targeted_Issue_List_2026-04-24.md - Targeted issue candidates derived from normalization packet
- CODE_REVIEW_STATUS_v1.0.md - Code review tracking
- COO_Runtime_Deprecation_Notice_v1.0.md - Component deprecation notice
- DEPRECATION_AUDIT_v1.0.md - Deprecation tracking
- governance_digest_v1.0.md - Governance activity summary
- IMPLEMENTATION_PLAN_v1.0.md - Meta-level implementation plan
- STEWARD_ARTEFACT_MISSION_v1.0.md - Artefact stewardship mission
- TASKS_v1.0.md - Meta-level task tracking
- LifeOSTechnicalArchitectureDraftV1.2SignedOff.md - Historical architecture signoff

## Archived Files

Historical review packets moved to **archive/2026-02_historical_reviews/**:
- Review_Packet_Add_timestamp_marker_0_v1.0.md
- Review_Packet_CI_Regression_Closure_v1.0.md

See [archive/2026-02_historical_reviews/README.md](archive/2026-02_historical_reviews/README.md) for disposition details.

## Organization

This directory is the home for repository-level control surfaces that do not belong inside runtime canon or governance rulings. Architecture authority still lives in canonical governance / architecture docs; this directory contains orientation, deltas, and draft control artefacts.

## Related Directories

- **docs/11_admin/**: Administrative state and backlog
- **docs/01_governance/**: Governance rulings and contracts
- **docs/99_archive/**: Historical archive

## Status

Active - meta-documentation and architecture-control surfaces maintained here.
