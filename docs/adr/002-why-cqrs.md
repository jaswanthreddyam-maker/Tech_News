# ADR-002: Why CQRS

## Status
Accepted

## Context
The platform must support complex analytical queries (e.g., Knowledge Graph relationships, Recommendations) while handling high-throughput write operations (e.g., Editorial workflow, tracking events).

## Decision
We separate the read and write models using Command Query Responsibility Segregation (CQRS). Writes execute business logic and emit events. Reads query specialized projection tables updated asynchronously.

## Consequences
- Independent scaling of read and write workloads.
- Read models can be completely dropped and rebuilt from events.
- Domain models are unpolluted by complex JOIN requirements.
- Eventual consistency is introduced.

## Alternatives Considered
- CRUD with complex JOINs (Rejected: poor scaling for graph relationships and analytics).
