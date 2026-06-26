# ADR-001: Why EventEnvelope exists

## Status
Accepted

## Context
Cross-subsystem communication in a monolithic or microservice architecture often leads to synchronous coupling, deep dependency chains, and cascading failures. We need a way to decoupled components while retaining deterministic state.

## Decision
We mandate that all cross-subsystem communication occurs via immutable EventEnvelopes routed through an Event Bus. The EventEnvelope provides a strict schema (provider, event_type, subject_id, payload, timestamps).

## Consequences
- Systems are completely decoupled.
- We have an immutable, replayable history of the entire system.
- Components never make synchronous REST calls to each other.
- Event structure cannot be changed (only new versions).

## Alternatives Considered
- Direct synchronous API calls (Rejected: leads to coupling).
- Shared database tables for inter-module queues (Rejected: breaks boundary encapsulation).
