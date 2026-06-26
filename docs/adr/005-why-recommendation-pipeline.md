# ADR-005: Why Recommendation Pipeline

## Status
Accepted

## Context
Recommendation generation often devolves into a monolithic script that retrieves, scores, and filters in an entangled way, making it impossible to reuse filters or inject generic diversification logic.

## Decision
We formalized a strict, multi-stage pipeline: Retrieve -> Validate -> Filter -> Score -> Sort -> Diversify -> Explain -> PostProcess.

## Consequences
- Reusable RecommendationFilters (e.g., AlreadyRead, Language).
- Universal diversification (e.g., penalizing repeated topics).
- Easy granular telemetry per stage.
- Clearer separation of concerns.

## Alternatives Considered
- Allowing capabilities to handle the entire recommendation logic internally (Rejected: leads to duplicated filtering and sorting logic).
