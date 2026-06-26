# RC2.2 Certification: Projection Replay & Transactional Outbox

## Certification Overview
**Date:** June 23, 2026
**Target:** Tech News Today v1.0.0-rc2.2 (Phase 1)
**Scope:** Verification of the Transactional Outbox Pattern and CQRS Projection Replay Idempotency.
**Constraint:** 0 Silent Failures. All business state transitions must originate from a versioned domain event.

---

## Executive Summary
The system successfully guarantees that Newsletter Subscribers and their corresponding `NewsletterSubscriptionCreated` events are persisted atomically via a Transactional Outbox. Furthermore, projection replays are guaranteed to be idempotent by checking the event UUIDs against the Timeline metadata.

## Architectural Validation

### 1. Transactional Outbox Pattern
**Status:** PASSED
* **Implementation:** The `NewsletterService.subscribe` method writes the `NewsletterSubscriber` and the `EventOutbox` payload within the same uncommitted transaction. A subsequent `flush()` and API-level `commit()` ensures that both records are written to the database atomically.
* **Validation:** If the database crashes after writing the subscriber, the outbox event is not lost. The subscriber exists ⇔ Outbox Event exists. This eliminates the silent failure class where a subscriber is created but the background event is dropped.

### 2. Projection Replay Idempotency
**Status:** PASSED
* **Implementation:** When `NewsletterSubscriptionCreated` events are dispatched from the outbox to the CQRS read models, the system checks the `TimelineNode` metadata for `outbox_event_id`. 
* **Validation:** If the projection engine is forced to replay events from the stream, duplicate events are safely ignored because the `TimelineNode` enforces exactly-once processing.

## Conclusion
The Transactional Outbox and Projection Replay systems are certified and constitutionally compliant.
