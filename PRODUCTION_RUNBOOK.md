# Production Runbook — Tech News Today v1.0.0

> This document provides step-by-step operational procedures for deploying,
> monitoring, troubleshooting, and maintaining Tech News Today in production.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Deployment](#deployment)
3. [Rollback](#rollback)
4. [Monitoring & Alerting](#monitoring--alerting)
5. [Incident Response](#incident-response)
6. [Backup & Recovery](#backup--recovery)
7. [Scaling](#scaling)
8. [Maintenance](#maintenance)

---

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  Cloudflare  │────▶│   Vercel     │     │  AWS ECS     │
│  CDN / DNS   │     │  (Frontend)  │────▶│  (Backend)   │
└─────────────┘     └─────────────┘     └──────┬───────┘
                                               │
                         ┌─────────────────────┼─────────────────────┐
                         │                     │                     │
                    ┌────▼────┐          ┌─────▼─────┐        ┌─────▼─────┐
                    │ Postgres │          │   Redis    │        │  Celery   │
                    │ pgvector │          │  (Cache)   │        │ (Workers) │
                    └──────────┘          └───────────┘        └───────────┘
```

| Service | Technology | Hosting |
|---------|-----------|---------|
| Frontend | Next.js 15 (React 19) | Vercel |
| Backend | FastAPI + Uvicorn | AWS ECS/Fargate |
| Database | PostgreSQL 16 + pgvector | Managed RDS |
| Cache | Redis 7 | Managed ElastiCache |
| Workers | Celery | AWS ECS/Fargate |
| CDN | Cloudflare | Cloudflare |
| Monitoring | Sentry + Custom Telemetry | Sentry Cloud |

---

## Deployment

### Prerequisites

- [ ] All CI gates passing on `main` branch
- [ ] Release checklist completed (`RELEASE_CHECKLIST.md`)
- [ ] Versions aligned: `package.json`, `PROJECT_STATE.md`, `CHANGELOG.md`
- [ ] Database migrations reviewed and approved

### Frontend (Vercel)

```bash
# Vercel auto-deploys from main branch
# Manual deploy if needed:
vercel --prod
```

**Verification:**
1. Check Vercel deployment status
2. Verify `/_next/` static assets load
3. Check PWA manifest at `/manifest.json`
4. Verify Service Worker at `/sw.js`

### Backend (AWS ECS)

```bash
# 1. Build and push Docker image
docker build -t tech-news-backend -f backend/Dockerfile.dev .
docker tag tech-news-backend:latest <ECR_REPO>:$VERSION
docker push <ECR_REPO>:$VERSION

# 2. Update ECS service
aws ecs update-service --cluster tech-news --service backend --force-new-deployment

# 3. Monitor deployment
aws ecs wait services-stable --cluster tech-news --services backend
```

**Verification:**
1. `curl https://api.example.com/api/v1/health/live` → `200 OK`
2. `curl https://api.example.com/api/v1/health/ready` → `200 OK`
3. Check ECS task count matches desired

### Database Migrations

```bash
# ALWAYS run migrations BEFORE deploying new code
# 1. Connect to production database
# 2. Run migrations
cd backend && alembic upgrade head

# 3. Verify
alembic current
alembic check  # Should show no drift
```

> [!CAUTION]
> Never run `alembic downgrade` in production without explicit approval.
> Use the rollback procedure instead.

---

## Rollback

### Frontend Rollback

```bash
# Vercel: instant rollback to previous deployment
vercel rollback
```

### Backend Rollback

```bash
# 1. Identify the previous task definition revision
aws ecs describe-services --cluster tech-news --services backend \
  | jq '.services[0].taskDefinition'

# 2. Update to previous revision
aws ecs update-service \
  --cluster tech-news \
  --service backend \
  --task-definition tech-news-backend:<PREVIOUS_REVISION>

# 3. Wait for stability
aws ecs wait services-stable --cluster tech-news --services backend

# 4. Verify
curl https://api.example.com/api/v1/health/ready
```

### Database Rollback

```bash
# Only if migration caused issues
# 1. Identify current revision
cd backend && alembic current

# 2. Downgrade one revision
alembic downgrade -1

# 3. Verify
alembic current
```

> [!WARNING]
> Database rollbacks may cause data loss if the migration added columns
> that received data. Always verify with a staging test first.

---

## Monitoring & Alerting

### Health Endpoints

| Endpoint | Purpose | Expected |
|----------|---------|----------|
| `/api/v1/health/live` | Liveness probe | `200` always |
| `/api/v1/health/ready` | Readiness probe | `200` when DB + Redis connected |

### Key Dashboards

- **Sentry**: Error tracking and performance monitoring
- **Admin Command Center**: `/admin` — Source health, article pipeline, AI queue, infrastructure
- **Telemetry**: Real-time SSE stream at `/api/v1/telemetry/stream`

### Alert Channels

| Severity | Channel | Response Time |
|----------|---------|---------------|
| Critical (P0) | Sentry + Slack/Discord | 15 minutes |
| High (P1) | Sentry + Email | 1 hour |
| Medium (P2) | Sentry | 4 hours |
| Low (P3) | Weekly review | Next sprint |

### SLOs

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| Homepage p95 | < 500ms | > 750ms |
| Search p95 | < 700ms | > 1000ms |
| Recommendations p95 | < 600ms | > 900ms |
| Article p95 | < 400ms | > 600ms |
| AI Summary p95 | < 8s | > 12s |
| Availability | 99.9% | < 99.5% |
| Error Rate | < 0.1% | > 0.5% |

---

## Incident Response

### Severity Levels

| Level | Description | Example |
|-------|-------------|---------|
| **P0** | Service down, all users affected | Database unreachable |
| **P1** | Major feature broken | Search returns errors |
| **P2** | Degraded performance | Slow response times |
| **P3** | Minor issue | UI glitch on one browser |

### Response Procedure

1. **Acknowledge** — Confirm the incident within the response time SLA
2. **Assess** — Determine severity and impact
3. **Communicate** — Post status update
4. **Mitigate** — Apply immediate fix or rollback
5. **Resolve** — Deploy permanent fix
6. **Postmortem** — Document root cause and prevention

### Common Incidents

#### Database Unreachable
```bash
# 1. Check RDS status
aws rds describe-db-instances --db-instance-identifier tech-news-db

# 2. Check security groups and VPC
# 3. Check connection pool exhaustion
# 4. Restart backend service if needed
aws ecs update-service --cluster tech-news --service backend --force-new-deployment
```

#### Redis Unreachable
```bash
# 1. Check ElastiCache status
aws elasticache describe-cache-clusters

# 2. Application should degrade gracefully (circuit breaker)
# 3. Restart Redis if needed
```

#### AI Provider Outage (OpenAI)
```bash
# Application has circuit breakers for AI endpoints
# Users will see cached/fallback content
# Monitor: https://status.openai.com
```

#### High Error Rate
```bash
# 1. Check Sentry for error patterns
# 2. Check recent deployments
# 3. Check infrastructure health
curl https://api.example.com/api/v1/health/ready
# 4. Rollback if caused by deployment
```

---

## Backup & Recovery

### Automated Backups

| Resource | Frequency | Retention |
|----------|-----------|-----------|
| PostgreSQL | Daily snapshots | 30 days |
| Redis | RDB snapshots | 7 days |

### Manual Backup

```bash
# Trigger manual backup
python backend/scripts/trigger_backup.py

# Verify backup
python backend/scripts/trigger_backup.py --verify
```

### Restore Procedure

```bash
# 1. Stop the backend service
aws ecs update-service --cluster tech-news --service backend --desired-count 0

# 2. Restore database
python backend/scripts/trigger_restore.py --backup-id <BACKUP_ID>

# 3. Verify data integrity
python backend/scripts/trigger_restore.py --verify

# 4. Restart backend
aws ecs update-service --cluster tech-news --service backend --desired-count 2

# 5. Run health checks
curl https://api.example.com/api/v1/health/ready
```

### Point-in-Time Recovery

```bash
# AWS RDS supports PITR within the backup retention window
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier tech-news-db \
  --target-db-instance-identifier tech-news-db-recovery \
  --restore-time "2026-06-12T00:00:00Z"
```

---

## Scaling

### Horizontal Scaling

```bash
# Scale backend
aws ecs update-service --cluster tech-news --service backend --desired-count 4

# Scale workers
aws ecs update-service --cluster tech-news --service worker --desired-count 4
```

### Vertical Scaling

Update task definitions with increased CPU/memory:
- Backend: 1 vCPU / 2GB → 2 vCPU / 4GB
- Workers: 1 vCPU / 2GB → 2 vCPU / 4GB

### Auto-Scaling Triggers

| Metric | Scale Up | Scale Down |
|--------|----------|------------|
| CPU Utilization | > 70% | < 30% |
| Request Count | > 1000 req/min | < 200 req/min |
| Queue Depth | > 100 tasks | < 10 tasks |

---

## Maintenance

### Dependency Updates

```bash
# Backend
cd backend
pip install pip-audit
pip-audit -r requirements.txt

# Frontend
cd frontend
npm audit
npm outdated
```

### Database Maintenance

```bash
# Vacuum and analyze (run during low-traffic)
psql -h <HOST> -U postgres -d tech_news_today -c "VACUUM ANALYZE;"

# Check index health
psql -h <HOST> -U postgres -d tech_news_today -c "
  SELECT schemaname, tablename, indexname, idx_scan
  FROM pg_stat_user_indexes
  ORDER BY idx_scan ASC
  LIMIT 20;
"
```

### Log Rotation

Logs are managed by the hosting platform (Vercel, AWS CloudWatch).
Backend structured JSON logs are emitted via `structlog`.

### Certificate Renewal

Managed by Cloudflare (automatic).

---

> **Last Updated**: Phase 6J — Release Engineering & Production Validation
