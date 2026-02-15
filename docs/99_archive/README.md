# LifeOS Historical Archive (docs/99_archive/)

Immutable historical reference archive for superseded LifeOS documentation.

**Archive Status:** Reorganized 2026-02-14 during documentation consolidation (Batch 2, P1)

## Structure

All archived content is organized into dated subdirectories with max depth 2:

| Dated Subdir | Period | Contents |
|--------------|--------|----------|
| **2024-12_initial/** | Early 2024 - Dec 2024 | Legacy structures, early governance, initial runtime specs |
| **2025-06_v1_sunset/** | 2025 H1 | LifeOS v1 era documents, superseded protocols |
| **2026-01_constitution_v2/** | Jan 2026 | Constitution v2.0 transition archives |
| **2026-01_governance_updates/** | Jan 2026 | Governance logs and updates |
| **2026-02_pre_consolidation/** | Feb 2026 | Pre-consolidation root-level archive files |

## Invariants (I-ARCHIVE-IMMUTABLE)

1. **All files in this archive are IMMUTABLE** - preserved for historical reference only
2. **Do not link to archived files** from active documentation (see I-NO-INBOUND-ARCHIVE-LINKS)
3. **Do not resurrect archived content** - current active docs are canonical
4. **Max depth: 2** - dated subdirs may contain subdirs but no deeper nesting

## Allowed Links

Per global archive link ban policy (I-NO-INBOUND-ARCHIVE-LINKS):

- ✅ Archive README.md files may link to archived files **within their own dated subdir**
- ✅ Directory READMEs may link to **archive README.md files only** (not individual archived files)
- ❌ Active docs must NOT link to any archived files

## Disposition Index

Each dated subdirectory contains a README.md describing:
- **Contents**: What types of documents are archived there
- **Disposition**: Why archived, what superseded them
- **Do not resurrect**: Warning against using archived content

For detailed file-level disposition tables, see individual dated subdir READMEs:
- [2024-12_initial/README.md](2024-12_initial/README.md)
- [2025-06_v1_sunset/README.md](2025-06_v1_sunset/README.md)
- [2026-01_constitution_v2/README.md](2026-01_constitution_v2/README.md)
- [2026-01_governance_updates/README.md](2026-01_governance_updates/README.md)
- [2026-02_pre_consolidation/README.md](2026-02_pre_consolidation/README.md)

## Canonical Active Documentation

**Instead of using archived files, refer to:**

- **Constitution & Architecture**: docs/00_foundations/
- **Governance & Contracts**: docs/01_governance/
- **Protocols & Standards**: docs/02_protocols/
- **Runtime Specifications**: docs/03_runtime/
- **Navigation**: docs/INDEX.md

## Archive History

- **2026-02-14**: Reorganized from fragmented structure to dated subdirs (max depth 2)
  - Flattened deep nesting (legacy_structures/Specs/Archive → 2024-12_initial/Specs)
  - Moved topical subdirs (superseded/, meta_historical/, etc.) into dated subdirs
  - Created disposition READMEs for all dated subdirs
- **Pre-2026-02**: Accumulated archive files with fragmented organization (superseded/, legacy_structures/, etc.)

---

**Last Updated:** 2026-02-14 (Batch 2 consolidation)
