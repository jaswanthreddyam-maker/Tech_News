# Story Domain Design

## Context
Historically, Tech News Today utilized a flat `Article` entity model. This structure tightly coupled the concept of a "news event" with the individual artifacts reporting on it. As the platform transitions to an Editorial Intelligence model (RC3), it is necessary to decouple these concepts to support advanced capabilities like impact scoring, deduplication, and narrative evolution. 

This document defines the `Story` as a first-class domain entity and establishes its relationship to standard articles and editorial workflows.

## The Story Entity
A **Story** represents an overarching narrative, event, or topic (e.g., "The OpenAI Board Shakeup"). It is the parent entity to which individual `Article` artifacts are linked.

### Core Properties
- `id`: Unique identifier (UUID).
- `title`: A canonical, human-readable title summarizing the overarching narrative.
- `status`: The active tracking state of the story (see Story Status).
- `primary_article_id`: A reference to the definitive or initial breaking article that spawned the story.
- `impact_score`: An aggregate metric defining the relative value/engagement of the narrative (Design Only for RC3.1).
- `created_by`: Audit field identifying the editor or automated system that created the story.
- `created_at`: Timestamp of creation.
- `updated_at`: Timestamp of last mutation.

### Story Status Transitions
Story status operates independently of article publication states.
- **ACTIVE**: The story is ongoing, with frequent updates, high reader engagement, and active newsroom coverage.
- **MONITORING**: The initial surge of news has subsided, but the system/newsroom is watching for late-breaking follow-ups or regulatory fallout.
- **DORMANT**: The story has exited the immediate news cycle.
- **ARCHIVED**: The story is definitively concluded and requires no further active tracking.

## Relationship Constraints

### 1. Cardinality
An `Article` belongs to exactly **one** `Story`. 
```
Story (1) ---- (N) Article
```
A story can aggregate multiple articles (e.g., the breaking news report, the deep-dive analysis, the opinion piece). However, for simplicity and strict boundary control in v1, an article cannot belong to multiple distinct stories simultaneously.

### 2. Impact Ownership
`Impact` is an aggregate property measured across the `Story` domain. While individual articles generate telemetry (views, CTR, reads), the overarching *Story* accumulates these signals to determine its persistence, relevance, and lifecycle state.

## Advanced Capabilities (RC3.2 - RC3.4)
Introducing the Story domain unlocks the following future capabilities:

1. **Story Evolution**: Chronologically ordering the `N` articles within a `Story` to build a timeline of the narrative.
2. **Duplicate Detection**: Ingesting similar articles from disparate RSS sources and automatically absorbing them into the same `Story` entity rather than surfacing redundant content to the homepage.
3. **Related Coverage**: Suggesting adjacent `Stories` that share semantic similarity or entity overlaps.
4. **Coverage Monitoring**: Tracking which active `Stories` lack sufficient `Articles` relative to their search volume or general popularity, signaling gaps to the editorial team.
