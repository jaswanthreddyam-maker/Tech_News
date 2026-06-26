# ADR-003: Why Projection Engine

## Status
Accepted

## Context
When maintaining dozens of read models across Analytics, Knowledge Graph, and Recommendations, managing state updates manually becomes error-prone, leading to duplicate processing or missed events.

## Decision
We implemented a Universal Projection Engine. It provides deterministic replay, idempotent projection mutations (MergeMutation, UpsertMutation, AppendMutation), dead-letter queues, and checkpoint tracking (ProjectionCheckpoint).

## Consequences
- Projectors are pure functions that return mutations.
- The Engine handles the database writes and idempotency.
- Exact replayability is guaranteed without double-counting.

## Alternatives Considered
- Ad-hoc event handlers executing SQL directly (Rejected: breaks idempotency and complicates replay).
