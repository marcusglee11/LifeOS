# Memory

Phase 1 durable memory records live here only after COO manual review and repo
merge. Records require validated YAML front matter, non-empty provenance, and
`writer: COO`.

Hermes, OpenClaw, EAs, and advisory agents must not write durable records here.
They emit candidate packets into `knowledge-staging/` instead.
