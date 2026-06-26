# ADR-006: Why Editorial OS

## Status
Accepted

## Context
Content management systems typically edit active records in place. This breaks audibility, prevents structured peer review, and complicates resolving concurrent edits or maintaining a historical record of what was published when.

## Decision
We implemented a git-like Editorial OS utilizing draft patches, discussion threads, fact-checking workflows, and immutable Publication Certificates. Published records are never mutated in place.

## Consequences
- 100% auditability for editorial actions.
- Easy rollback and version comparison.
- Robust review workflows natively integrated.

## Alternatives Considered
- Standard CRUD rticles table with a status column (Rejected: impossible to handle complex editorial history and concurrent revisions).
