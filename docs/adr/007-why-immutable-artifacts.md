# ADR-007: Why Immutable Artifacts

## Status
Accepted

## Context
Historical platform artifacts—such as publication records, AI session transcripts, and evidence trees—represent point-in-time snapshots of complex, legally or factually significant actions.

## Decision
We mandate that historical artifacts are strictly immutable. They are stored as append-only records, sometimes backed by Content-Addressable Storage (CAS) principles or checksums, to guarantee tamper-proof integrity.

## Consequences
- Simplified debugging and compliance audits.
- No risk of accidental retroactive data corruption.
- Clear lineage for knowledge verification.

## Alternatives Considered
- Updating existing artifacts (Rejected: destroys the point-in-time integrity required by an enterprise platform).
