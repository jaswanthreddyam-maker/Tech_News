# ADR-008: Why AI Thumbnail Recovery

## Status
Accepted

## Version
v1

## Modification Policy
Extension Only (No modifications to core principles; extensions allowed only to integrate additional providers or metrics).

## Context
Tech News Today requires high visual quality for its news artifacts. Thumbnails are normally provided deterministically by the source sites. However, many sites implement active scraping defenses, serve broken images, or explicitly forbid hotlinking/downloading of thumbnail assets. This results in articles lacking compelling visuals and forces the platform to rely on static fallback images, severely degrading the editorial presentation.

To solve this, we required a capability to automatically recover a thumbnail for an article. Given the diverse and unpredictable nature of the missing visuals, static logic is insufficient. We evaluated AI Generative Image generation to dynamically produce editorial illustrations that match the article's semantics.

However, treating AI Generation as just another thumbnail source risks obscuring underlying bugs (e.g. failing scrapers) and producing inappropriate or hallucinatory imagery. Therefore, the implementation of AI Thumbnail Generation must be strictly governed as a **recovery capability** rather than a primary ingestion mechanism.

## Key Decision
**AI Thumbnail Generation is a governed recovery capability, not a primary thumbnail acquisition mechanism.**

The system will only attempt AI thumbnail generation when all other deterministic ingestion and acquisition paths have explicitly failed or returned `NO_IMAGES_FOUND`.

## Constitutional Alignment
The implementation of the AI Thumbnail Recovery subsystem strictly adheres to the Tech News Today Architectural Constitution:

1. **Deterministic Before Intelligent**: The platform MUST exhaust all deterministic extraction strategies (e.g., OpenGraph, meta tags, JSON-LD) before escalating to the AI recovery subsystem.
2. **Explainability Over Magic**: A multi-stage generation process is used. First, an AI model (Gemini) evaluates the article and produces a structured *Thumbnail Specification*. Second, this specification is passed to an image generation model (Imagen/OpenAI). This guarantees that we know exactly *why* and *how* an image was generated, and what prompt was used, preventing black-box execution.
3. **Every AI Execution Emits an Audit Event**: Every successful or failed AI execution emits an auditable event (e.g., `AIThumbnailGenerated`, `AIThumbnailRejected`, `AIThumbnailGenerationFailed`). The exact `confidence` score and model versions are persistently stored in `AIThumbnailMetadata`.

## Prohibited Behavior
To maintain system integrity, observability, and certification status, the AI Thumbnail Recovery system is strictly governed by these constraints.

**AI generation must never compensate for:**
- Worker failures or queue backlogs.
- Projection or synchronization failures.
- Ingestion pipeline parsing bugs.
- General infrastructure outages.
- API Rate limiting issues (e.g., HTTP 429 from news sources).

**Failure Domain Separation**:
- Semantic ambiguity (i.e. an article lacks visual elements, resulting in low confidence) emits `AIThumbnailRejected`.
- Infrastructure failure (e.g., missing SDKs, Provider API timeouts) emits `AIThumbnailGenerationFailed`.
These two domains must remain entirely disjoint to ensure accurate Root Cause Analysis (RCA) operations.

## Consequences
- **Positive:** Reduces the frequency of static fallback images, improving presentation quality automatically. Maintains full observability. Ensures that bugs in the primary ingestion pipeline are not masked by AI.
- **Negative:** Adds complexity to the Celery ingestion worker. Introduces external dependencies on LLMs and Image Generative providers, necessitating circuit breakers, budget enforcement, and robust error handling.
