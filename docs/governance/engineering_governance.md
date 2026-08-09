# Engineering Governance Specification v1.0.0 — Feature-Freeze & Release Gate Policy

This document governs engineering execution for Tech News Today. It does not describe system architecture in detail.
It defines:
• What engineers are allowed to change.
• What constitutes a completed sprint.
• How production readiness is measured.
• When architecture changes are permitted.

---

## Executive Governance Status

```text
Architecture Version: 1.0.0
Status: FROZEN

Allowed Scope:
  ✔ Runtime Wiring & Integration
  ✔ Legacy Execution Path Removal
  ✔ Automated Testing & Chaos Validation
  ✔ Performance Optimization
  ✔ System Reliability & Security
  ✔ UI / UX Polish
  ✔ Documentation & Telemetry

Strictly Prohibited:
  ✘ New services or helpers
  ✘ New managers or coordinators
  ✘ New registries or factories
  ✘ New orchestrators
  ✘ New domain models or aggregates
  ✘ Speculative abstractions
```

---

## 1. Feature Proposal Decision Tree & Evidence Requirement

```text
When a new feature or refactor is proposed:

1. Does an existing component already solve this?
     │
    YES ──► Extend existing component.
     │
     NO
     ▼
2. Can an existing component be modified?
     │
    YES ──► Modify existing component.
     │
     NO
     ▼
3. Is a new abstraction absolutely necessary?
     │
     NO ──► REJECT proposal.
     │
    YES ──► Submit Architecture Decision Record (ADR) & REPLACE an existing abstraction.
```

### Evidence Over Opinion Policy
Any proposed architecture or refactoring change **MUST** include one of the following empirical proofs:
- [ ] Failing automated test.
- [ ] Reproducible production log traceback.
- [ ] Measured benchmark performance regression.
- [ ] Security vulnerability finding.
- [ ] Measurable KPI threshold regression.

---

## 2. Governance Priority Hierarchy & Architecture Change Policy

When two engineering priorities conflict, engineers evaluate trade-offs using the strict **Governance Hierarchy**:

$$\text{1. Security} \longrightarrow \text{2. Data Integrity} \longrightarrow \text{3. Runtime Correctness} \longrightarrow \text{4. Reliability} \longrightarrow \text{5. Performance} \longrightarrow \text{6. Developer Experience} \longrightarrow \text{7. Documentation}$$

### Core Engineering Rules
1. **Use Existing Architecture First**: Always leverage existing domain models, read projections, and services.
2. **Wire Existing Modules Before Creating New Ones**: Complete the wiring of implemented helper modules (`RSSService`, `ExtractionService`, `PersistenceService`).
3. **Refactor Only On Measurable Production Evidence**: Refactoring must be justified by runtime logs, metrics, or concrete performance bottlenecks.
4. **No New Abstractions Without Removing an Older One**: Maintain a zero net-growth cap on architectural complexity.
5. **Runtime Caller Enforcement**: No module may be merged without an active, verified caller in the live execution flow.
6. **Legacy Removal Rule**: Every completed migration must remove the legacy implementation within the same PR. No duplicate execution paths allowed.

### Architecture Change Policy
Architecture PRs are **prohibited unless they satisfy the Architecture Change Policy**. An exception is permitted **ONLY** if ALL five of the following conditions are met:
1. Production issue is reproduced with concrete logs/telemetry.
2. Existing architecture cannot solve the issue.
3. Performance or system reliability is measurably impacted.
4. An Architecture Decision Record (ADR) is submitted and approved.
5. An existing abstraction is removed or simplified in exchange.

---

## 3. Definition of Done (DoD) & Sprint Closeout Requirements

Every sprint must end with a formal completion report saved to `docs/reports/sprint-<letter>.md` using the standard 12-section schema:

### Standardized Sprint Completion Report Schema
```text
1. Objective
2. Files Modified
3. Runtime Wiring Audit
4. Legacy Code Removed
5. Tests Executed
6. KPI Results
7. health.bat Status
8. doctor.bat Status
9. status.bat Status
10. Definition of Done Checklist
11. Deferred Items
12. Next Sprint
```

- [ ] **Runtime Wiring Audit**: All component callers verified.
- [ ] **Legacy Path Audit**: 0 legacy execution paths remaining for migrated code.
- [ ] **KPI Report**: Performance metrics within release gate thresholds.
- [ ] **Definition of Done Checklist**:
  - [ ] **Runtime Caller Exists**: Verified caller in the live execution pipeline.
  - [ ] **Observable in UI/API**: Verified via `http://localhost:3000` or API endpoint.
  - [ ] **Automated Tests Pass**: `python tests/golden_dataset/verify_pipeline.py` passes cleanly.
  - [ ] **`doctor.bat` Passes**: 0 environment configuration errors.
  - [ ] **`health.bat` Passes**: 100% HEALTHY & OPERATIONAL across all 4 tiers.
  - [ ] **`status.bat` Reports Healthy**: CQRS lag = 0, workers online, projection inspector healthy.
  - [ ] **Zero Legacy Code Remaining**: Legacy execution paths completely removed in the same PR.
  - [ ] **Documentation Updated**: Report saved to `docs/reports/`.

---

## 4. Engineering KPI Release Gate Thresholds

$$\text{Runtime Coverage} = \frac{\text{Number of release-required core components with verified runtime callers}}{\text{Total release-required core components}} \times 100\%$$

| KPI Metric | Target Release Threshold | Target Status |
| :--- | :---: | :---: |
| **Homepage API Response Time** | **< 50 ms** | Required |
| **Projection Build Latency** | **< 500 ms** | Required |
| **RSS Poll Cycle Speed** | **< 60 sec** | Required |
| **End-to-End Publish Latency (RSS $\rightarrow$ Homepage)** | **< 2 min** | Required |
| **Homepage Story Count** | **Exactly 10** | Required |
| **Duplicate Detection Precision** | **> 99%** | Required |
| **Trigram Dedup Query Latency** | **< 5 ms** | Required |
| **CQRS Projection Lag** | **< 1 sec (0 pending)** | Required |
| **Multi-Tier System Health** | **100% HEALTHY** | Required |
| **Release-Required Component Runtime Coverage** | **100%** | Required |
| **Legacy Duplicate Code Paths** | **0** | Required |
| **Ingestion Pipeline Failure Rate** | **< 1%** | Required |
| **Critical Architecture Debt** | **0** | Required |
| **High Severity Architecture Debt** | **0** | Required |

---

## 5. Sprint Execution Roadmap & Closeout Reports

- [Sprint A Completion Report](file:///d:/tech_news/docs/reports/sprint-a.md) (`RSSService` Wiring & Legacy Removal) — **100% PASSED**
- [Sprint B Completion Report](file:///d:/tech_news/docs/reports/sprint-b.md) (`ExtractionService` Wiring & Legacy Removal) — **100% PASSED**
- [Sprint C Completion Report](file:///d:/tech_news/docs/reports/sprint-c.md) (`PersistenceService` Wiring & Legacy Removal) — **100% PASSED**
- [Sprint D Completion Report](file:///d:/tech_news/docs/reports/sprint-d.md) (Chaos & Stress Validation Testbed) — **100% PASSED**
- [Sprint E Completion Report](file:///d:/tech_news/docs/reports/sprint-e.md) (Homepage Rendering, Media Resilience & Reading Experience) — **100% PASSED**
- **Release Candidate 1 (RC1)**: Production Readiness Certification (7-Pillar Audit & Release Gate Validation) prior to `v1.0.0` tagging.

---

## 6. Release Candidate 1 (RC1) — Production Certification Gate

```text
Functional Validation
├─ Homepage renders exactly 10 stories
├─ Feed renders correctly
├─ Search returns expected results
├─ Article page renders correctly
├─ Reading Desk operational
├─ Bookmarks operational
└─ Resume Reading operational

Performance Validation
├─ Lighthouse ≥95
├─ Homepage API <50ms
├─ Projection build <500ms
└─ RSS→Homepage latency <2 min

Reliability Validation
├─ Redis restart recovery
├─ PostgreSQL restart recovery
├─ Celery restart recovery
└─ Docker restart recovery

Security Validation
├─ No exposed secrets
├─ JWT authentication verified
├─ RBAC verified
├─ SQL injection tests
└─ XSS tests

Observability Validation
├─ doctor.bat PASS
├─ health.bat PASS
├─ status.bat PASS
└─ No ERROR logs during 24h soak test

Release Approval
├─ All KPIs green
├─ Release-required runtime coverage 100%
├─ Legacy code paths = 0
├─ Critical & High severity architecture debt = 0
└─ Version tagged v1.0.0
```

---

## 7. Projection-Driven Non-Blocking Thumbnail FSM & Active Usage Policy

To prevent network delays from blocking projection publishing while eliminating disk bloating and repeated failure retries:

```text
Projection Candidates ─────────────► Projection Builder ────► Publish Projection IMMEDIATELY (<50ms)
       │                                                               ▲
       ▼                                                               │
Thumbnail Queue ───────────► FSM Evaluation ──► ArticleThumbnailUpdated Event
```

### Thumbnail Finite State Machine (FSM) States
- **`MISSING`**: Candidate article selected for a CQRS projection.
- **`QUEUED`**: Thumbnail request added to asynchronous background worker queue.
- **`DOWNLOADING`**: Image stream being fetched over network asynchronously.
- **`PROCESSING`**: Converted to WebP format, resized to 1200×675, raw original `.jpg`/`.png` deleted immediately.
- **`READY`**: WebP stored on disk (~100 KB), metadata saved in DB. `ArticleThumbnailUpdated` event emitted.
- **`FAILED` / `RETRYING`**: Retried up to 3 times with exponential backoff.
- **`PERMANENT_FAILURE`**: Terminal state reached after 3 failed attempts. Retry attempts stop permanently. Fallback image rendered permanently.

### Active Usage Disk Cleanup Policy
> **Governance Policy**: Thumbnail deletion must be based on **active usage** rather than simple article age. The specific implementation mechanism (reference counting, projection membership, reachability analysis, etc.) is an implementation detail and may evolve without changing the overall architecture.
