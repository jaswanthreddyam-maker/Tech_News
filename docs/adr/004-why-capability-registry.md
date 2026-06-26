# ADR-004: Why Capability Registry

## Status
Accepted

## Context
The platform must support multiple strategies for domains like Distribution (Email, RSS) and Recommendations (Trending, Related, ForYou), which change frequently as product requirements evolve.

## Decision
We enforce the Capability Registry pattern. Features are registered with a unified interface (RecommendationCapability, DistributionCapability) declaring ersion, priority, and cost. Algorithms are isolated and pluggable.

## Consequences
- Core orchestration code never changes when a new algorithm or channel is added.
- A/B testing is trivial.
- Clear contractual boundaries for new product features.

## Alternatives Considered
- Hardcoded if/else logic in services (Rejected: brittle and violates Open/Closed principle).
