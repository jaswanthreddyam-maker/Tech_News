# Tech News Today — Engineering Handbook

*This handbook defines "How" we build, ensuring code complies with the Architecture Constitution.*

---

## ✅ Definition of Done

A feature is complete only when:
- [ ] Functional requirements implemented
- [ ] Architecture Constitution satisfied
- [ ] Required ADRs updated
- [ ] Maturity Level ≥ 2 (Observable)
- [ ] Health endpoint implemented
- [ ] Metrics exposed
- [ ] Structured logs emitted
- [ ] Replay strategy documented
- [ ] Regression tests passing
- [ ] Documentation updated

---

## 📈 Subsystem Maturity Model

Every new feature and subsystem must evolve through these operational stages. *Maturity evolves; the Constitution does not.*

- **Level 1 — Functional:** Feature works as intended.
- **Level 2 — Observable:** Exposes Health, Metrics, and Logs.
- **Level 3 — Recoverable:** Supports Replay, Retry, and Reconstruction.
- **Level 4 — Autonomous:** Features Self-healing and Automated diagnostics.
- **Level 5 — Adaptive:** Employs Predictive operations and AI-assisted optimization.

---

## 🛠️ Engineering Standards (Skeleton)

*To be expanded as the team grows.*

### 1. Coding Conventions
- Strictly typed Python/TypeScript.
- No silent `except Exception: pass` blocks without metric emission.

### 2. Logging Standards
- All logs must be structured JSON in production.
- Include `correlation_id`, `event_type`, and `subsystem` in every log.

### 3. Metric Naming
- Prometheus format: `[namespace]_[subsystem]_[metric_name]_[unit]`
- Example: `tnt_cqrs_projection_duration_seconds`

### 4. Event Naming
- Domain events must be past-tense verbs: `ArticlePublished`, `ThumbnailExtracted`.

### 5. Git Workflow & Release Process
- Feature branches (`feature/`, `fix/`, `ops/`) -> PR -> Squash Merge to `main`.
- SemVer tags for releases (`v1.0.0-rc2`).

### 6. Testing Philosophy
- Deterministic, isolated databases for integration tests.
- Fail-fast guards enabled in all testing environments to protect development data.
