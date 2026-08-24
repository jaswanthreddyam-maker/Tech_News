# Tech News Today — Architecture Manifesto & Baseline Contract

**Version:** 1.0.0  
**Status:** FROZEN 🧊  
**Architecture Freeze Date:** 2026-08-24  
**Verification Suite:** 76/76 Passed | ACE Compliance: 100.0% (Grade A+)  

The foundational architecture for **Tech News Today** is officially **FROZEN**.

This document serves as the project's constitution. It outlines the core subsystems, mechanical invariants, dependency rules, reliability contracts, and extension points that govern all future development.

---

## 1. Frozen Subsystems

1. **Acquisition & Ingestion OS**: Manages external feed polling, robots/SSRF protection, content deduplication, and raw article persistence.
2. **Knowledge Engine**: Extracts entities, topics, timelines, and relationships into an immutable graph via CQRS and background projections.
3. **Editorial OS**: Manages git-like draft patches, discussion threads, reviews, fact-checking, and immutable publication certificates.
4. **Distribution OS**: Coordinates multi-channel distribution via the `DistributionPlanner`, `AudienceResolver`, and capability registry (Email, RSS, Webhook).
5. **Transactional Event Platform**: Outbox-based asynchronous execution model guaranteeing at-least-once delivery with effect idempotency.
6. **Universal Projection Engine**: Targeted, replayable read-model synchronization using handler-level checkpoints and dead-letter routing.
7. **Analytics Platform**: Consumes events to project deterministic read models for business metrics without double-counting.
8. **Recommendation Platform**: Multi-stage pipeline (`Retrieve` → `Validate` → `Filter` → `Score` → `Sort` → `Diversify` → `Explain` → `PostProcess`) driven by capabilities and canonical profiles.

---

## 2. Core Invariants & Reliability Contracts

### Contract 1: At-Least-Once Delivery + Effect Idempotency
- The system operates under **at-least-once delivery semantics**. Workers may re-execute handlers upon network partitions, lease timeouts, or worker crashes.
- **Effect Idempotency**: Successfully committed side effects are guaranteed idempotent via `OutboxDispatchCheckpoint` (`UNIQUE(handler_name, outbox_event_id)`).
- Concurrent worker claiming is guarded by `WITH candidates AS (...) UPDATE ... FROM candidates ... FOR UPDATE SKIP LOCKED`.
- Expired leases (`lease_expires_at < NOW()`) are automatically reclaimed by subsequent dispatcher polls.
- The phrase "exactly-once execution" is forbidden in system specifications; the guarantee is strictly **at-least-once execution with idempotent committed effects**.

### Contract 2: Explicit Event Context & Handler Isolation
- Event metadata is never injected into domain payloads.
- Handlers receive explicit context: `handle(db, payload, event_id, event_type)`.
- Each handler executes in its own transaction commit/rollback boundary. If Handler A succeeds and Handler B fails, Handler A's checkpoint is preserved; on retry, Handler A is skipped and Handler B is retried.

### Contract 3: AI Provenance Invariant
- **Invariant:** *One `AIInferenceRecord` represents one immutable AI inference execution/result whose output can be traced to every domain artifact derived from that execution.*
- `AIInferenceRecord` is strictly append-only (forensic evidence capturing `provider`, `model`, `task_type`, `prompt_version`, `prompt_hash`, `input_fingerprint`, `source_article_id`).
- All knowledge graph entities (`ArticleEntityLink`) and edges (`RelationshipEdge`) maintain mandatory `inference_id` foreign keys.

### Contract 4: Architectural Capability Boundaries (ACE Enforced)
- **Domain Layer (`models/`, `schemas/`)**: Pure entities and contracts. Must NOT depend on Services, Background Tasks, Interface (API/CLI), or Infrastructure engines.
- **Application Layer (`services/`, `editorial/`, `tasks/`, `apps/`)**: Orchestrates domain use cases. Must NOT depend on the Interface layer (Inversion of Control).
- **Interface Layer (`api/`, `cli/`)**: Route handlers and CLI endpoints. Injects dependencies via FastAPI dependency injection and calls Application services.
- **Mechanically Enforced**: The Architecture Compliance Engine (ACE) runs via AST analysis in CI (`pr-gate.yml`) and blocks PRs on any `VIOLATION` severity finding.

### Contract 5: Observability & Span Security
- OpenTelemetry auto-instruments FastAPI, SQLAlchemy, Redis, and Celery.
- Meaningful business operations emit structured manual spans:
  - `outbox.dispatch_batch` & `outbox.dispatch_event`
  - `article.enrichment` (attributes: `ai.provider`, `ai.model`, `ai.tokens`, `ai.cost_usd`)
  - `article.knowledge_extraction` (attributes: `article.id`, `entities.count`, `relationships.count`)
- **Security Whitelist**: Raw prompts, payloads, and sensitive tokens never enter distributed traces.

---

## 3. Architecture Change Management Protocol

The architecture does not evolve organically. Any future architectural change requires an explicit **Architecture Change Record (ACR)**:

```text
Feature / Requirement
         ↓
Does existing architecture support it?
  ├── YES → Implement normally within existing capabilities
  │
  └── NO
       ↓
  Draft Architecture Change Record (ACR)
       ↓
  Boundary Impact Analysis & Threat Model
       ↓
  Architecture Guild Review & Calibration
       ↓
  Implementation + ACE Rule Update + Regression Suite
       ↓
  Version Bump (v1.1.0 / v2.0.0) → New Baseline
```

---

## 4. Verification Evidence (Baseline v1.0.0)

| Test Suite | Tests | Result | Focus |
|---|---|---|---|
| `test_outbox_hardening.py` | 8 | ✅ PASSED | SKIP LOCKED, crash recovery, DLQ, effect idempotency |
| `test_ai_provenance.py` | 3 | ✅ PASSED | Immutable forensic FK traceability |
| `test_ai_infrastructure.py` | 15 | ✅ PASSED | AI service, pricing, tokens, caching, timeouts |
| `test_thumbnail_projection.py` | 1 | ✅ PASSED | Targeted CQRS read-model sync |
| `test_unit_auth.py` | 16 | ✅ PASSED | RBAC, JWT, session lifecycle |
| `test_unit_config.py` | 1 | ✅ PASSED | Environment hierarchy & DB guards |
| `test_unit_html.py` | 5 | ✅ PASSED | Sanitization, XSS, attribute filters |
| `test_unit_observability.py` | 8 | ✅ PASSED | Metrics, counters, latency histograms |
| `test_unit_ranking.py` | 7 | ✅ PASSED | Ranking algorithms, decay curves |
| `test_unit_thumbnail.py` | 6 | ✅ PASSED | Candidate scoring, SSRF, in-memory validation |
| `ace/tests/test_layer_policy.py`| 6 | ✅ PASSED | Layer policy boundaries, negative tests |
| **Total** | **76** | **✅ 100%** | **Zero failures, zero regressions** |

**ACE Compliance:** Score: 100.0% (Grade A+) | 0 blocking violations | 0 advisory items
