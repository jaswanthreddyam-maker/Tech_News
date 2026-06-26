# Tech News Today - Architecture Manifesto

**Version:** 1.0  
**Status:** Frozen 🧊  
**Architecture Freeze Date:** 2026-06-14  
**Current Platform Version:** v1  

As of Phase 13, the foundational backend architecture for Tech News Today is officially **FROZEN**.

This document serves as the project's constitution. It outlines the core subsystems, architectural invariants, dependency rules, and extension points that must be respected by all future contributors. The goal is to ensure that the platform can scale, evolve, and support new product capabilities without fracturing its core primitives.

---

## 1. Frozen Subsystems

The backend is composed of eight deeply segregated, highly robust subsystems:

1. **AIOS Kernel**: The orchestration core. Handles planning, scheduling, deterministic execution, capability registration, and replay via the Operations Console.
2. **Knowledge Engine**: Extracts entities, timelines, and relationships into an immutable graph via CQRS and background projections.
3. **Editorial OS**: Manages git-like draft patches, discussion threads, reviews, fact-checking, and immutable publication certificates.
4. **Distribution OS**: Coordinates publishing pipelines via the `DistributionPlanner`, `AudienceResolver`, and capability registry (Email, RSS, Webhook).
5. **Event Platform**: The central nervous system. All cross-subsystem communication occurs via immutable `EventEnvelope`s routed through the Event Bus.
6. **Universal Projection Engine**: A highly robust, replayable engine utilizing idempotent mutations, checkpoints, and dead-letter queues to synchronize read models.
7. **Analytics Platform**: Consumes events to project deterministic, auditable read models for business and usage metrics without double-counting.
8. **Recommendation Platform**: An extensible, multi-stage pipeline (`Retrieve` → `Validate` → `Filter` → `Score` → `Sort` → `Diversify` → `Explain` → `PostProcess`) driven by capabilities and canonical profiles.

---

## 2. Architecture Freeze Policy

Frozen subsystems may **not** introduce:
- New dependencies
- New cross-subsystem references
- Breaking schema changes
- Synchronous coupling

Changes to frozen subsystems are **only permitted** if they are:
- Bug fixes
- Performance optimizations
- Security fixes
- Backward-compatible extension points

---

## 3. Breaking Change Policy

Breaking changes to frozen primitives are generally prohibited unless they explicitly address:
- Critical security issues
- Data corruption
- Legal or compliance requirements

If a breaking change is absolutely necessary, it requires:
- An RFC (Request for Comments)
- Architecture Review
- A formal Migration Plan
- Backward Compatibility Analysis

---

## 4. Dependency Matrix

To prevent accidental imports and cyclical dependencies, the allowed dependency graph is strictly defined:

| Module | Depends On |
| --- | --- |
| **AIOS** | Core |
| **Knowledge** | Core |
| **Editorial** | Core |
| **Distribution** | Core |
| **Analytics** | Core |
| **Recommendation** | Core + Analytics Read Models |
| **Growth (Phase 14)** | Analytics + Recommendation |
| **Enterprise (Phase 16)** | Everything (via strict APIs) |

---

## 5. Architectural Invariants

To maintain system integrity, the following rules are non-negotiable:

- **Immutable Events**: All state changes must be published as an immutable `EventEnvelope`. Events are never deleted or modified.
- **Strict Segregation**: Subsystems do not know about each other. They communicate solely by producing and consuming events.
- **Read Model Isolation**: Read models (e.g., Analytics, Recommendations, Knowledge Graph) are updated *only* through the Universal Projection Engine. Direct operational writes to these tables are strictly forbidden.
- **Idempotent Projections**: All projection mutations must be idempotent (e.g., using `MergeMutation` or `UpsertMutation` with conflict resolution) to allow safe, replayable processing from checkpoints.
- **Immutable History**: Editorial changes must preserve immutable version history. Published articles cannot be mutated in place; they require a patched revision.

---

## 6. Event Contract Policy

An `EventEnvelope` is immutable.
Fields inside an event payload may only be **added**. They must never be:
- Renamed
- Deleted
- Repurposed

If an event structure needs to change substantially, publish a new `event_type` (e.g., `ARTICLE_VIEWED_V2`).

---

## 7. Schema Evolution

- **Operational tables** may evolve (add columns, new indices).
- **Read models** may be dropped and entirely rebuilt via the Universal Projection Engine.
- **Event schemas** are strictly append-only.
- **Historical artifacts** (e.g., publication certificates) are strictly immutable.

---

## 8. Capability Contract

Every capability across the system (Distribution, Recommendation, etc.) must satisfy identical rules. Capabilities must:
- Declare a `version`
- Declare a `priority`
- Declare a `cost` (e.g., `LOW`, `MEDIUM`, `HIGH`)
- Declare supported subjects / contexts
- Be deterministic in execution
- Expose standardized telemetry

---

## 9. Testing Hierarchy

Every feature introduced to the platform requires testing at the following levels:
`Unit Tests` → `Integration Tests` → `Replay Tests` → `Determinism Tests` → `Telemetry Validation`

---

## 10. Performance Budget

Optimization is measurable. The platform adheres to strict latency budgets:
- **API**: < 300ms
- **Projection**: < 50ms/event
- **Recommendation**: < 100ms
- **Search**: < 200ms
- **Distribution Queue**: < 5s

---

## 11. Security Principles

The architecture naturally enforces deep security:
- **Least Privilege**: Components only access what they need.
- **Zero Trust**: Internal capabilities validate inputs robustly.
- **Immutable Audit Logs**: All state mutations generate an auditable event.
- **Secrets Never Stored**: No raw credentials stored in DB.

---

## 12. Versioning & Deprecation Policy

- **Capabilities**: When modifying an existing algorithm substantially, create a new version (e.g., `v2.0`) and run it side-by-side.
- **Legacy Events**: Legacy events are never removed from the schema. Projectors handle the routing.
- **Deprecation**: Deprecated capabilities are marked by setting their `priority` or `cost` such that they are bypassed before eventually being removed from the registry.

---

## 13. Observability Policy

To ensure production visibility, every capability and subsystem must emit:
- Structured logs (with bounded cardinality)
- Metrics (counters, gauges, histograms)
- Traces (spanning from API entry to projection exit)
- Correlation IDs attached to all cross-boundary requests

No subsystem may introduce opaque execution paths. If it runs, it must be observable.

---

## 14. Reliability Policy

The platform must degrade gracefully under duress. All subsystems adhere to these resilience patterns:
- **Idempotency**: All retries must be strictly idempotent.
- **Timeouts**: Mandatory timeouts on all synchronous operations.
- **Circuit Breakers**: Mandatory for all external provider calls.
- **Backoff**: Exponential backoff with jitter for retries.
- **DLQs**: Dead-letter queues (DLQs) for permanent projection or distribution failures.

---

## 15. Storage Policy

Data must reside in the appropriate persistence layer. The hierarchy is strict:
1. **Operational Database**: The transactional source of truth for core domains (e.g., Editorial, Users).
2. **Event Store**: The immutable ledger of all system state changes.
3. **Projection Read Models**: Derived, disposable tables optimized purely for querying.
4. **Caches**: Ephemeral storage (e.g., Redis). Never treated as a source of truth.
5. **External Search Index**: Optimized retrieval stores (e.g., Elasticsearch, Vector DBs), continuously hydrated from read models.

---

## 16. The Final Rule

> **Architecture serves the product.**
> When product requirements conflict with architectural purity, prefer extension through capabilities rather than modification of frozen primitives.

---

**Last Updated:** 2026-06-14  
**Approved By:** Principal Architect  
**Architecture Version:** 1.0  
