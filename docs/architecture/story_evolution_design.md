# Story Evolution Design

## Context
In RC3.1, we transitioned from an Article-centric domain to a Story-centric domain. A `Story` is a continuous narrative that encapsulates multiple `Article` entities over time. 
This document defines the architecture for how Stories are created, merged, split, and tracked, forming the prerequisite for RC3.2 (Cross-Article Intelligence).

## 1. Story Creation Strategy
Tech News Today employs a **Hybrid Creation Strategy**.

- **Auto-Creation (Ingestion):** When a new article is ingested and the duplicate detection / semantic matching algorithms fail to find an existing active `Story`, a new `Story` is automatically created.
- **Manual Creation (Editorial):** Editors can manually create a `Story` entity and explicitly assign articles to it from the editorial dashboard.

## 2. Story Merge Strategy
Duplicate detection might discover that two distinct stories are actually covering the exact same narrative (e.g., "OpenAI Funding Round" vs. "OpenAI New Investment").

### Merge Process
When `Story B` is merged into `Story A`:
1. All `Articles` belonging to `Story B` are re-assigned to `Story A`.
2. `Story B`'s status is changed to `ARCHIVED` or deleted.
3. The impact score of `Story A` is recalculated based on the newly expanded engagement metrics.

## 3. Story Split Strategy
A single story might evolve into two distinct narratives that warrant separate tracking (e.g., an ongoing lawsuit splitting into a settlement branch and a criminal trial branch).

### Split Process
1. A new `Story C` is created.
2. An editor explicitly selects a subset of `Articles` from `Story A` and re-assigns them to `Story C`.
3. The impact scores for both `Story A` and `Story C` are recalculated independently.

## 4. Story Timeline & Milestones
Because a `Story` has a 1->N relationship with `Article`s, the articles natively form a chronological timeline.

- **Timeline:** The chronologically ordered sequence of `PUBLISHED` articles attached to a `Story`.
- **Milestones:** Highly impactful articles within the timeline. An article is considered a milestone if it represents a significant shift in the narrative (e.g., the original breaking news, a major discovery).

## 5. Related Stories
Stories do not exist in isolation. The `Related Coverage Engine` (RC3.2) will semantically link related `Story` entities.
For example, the "Nvidia Earnings" story might be related to the "Global Chip Shortage" story.

## 6. Story Event Auditability
To ensure autonomous operations remain observable, the platform emits explicit domain events for all Story lifecycle operations into the CQRS `EventOutbox`.

### Required Events
- `StoryCreated`: Emitted upon auto or manual creation.
- `StoriesMerged`: Emitted when two stories are merged, detailing `source_story_id` and `target_story_id`.
- `StorySplit`: Emitted when articles are fractured into a new story, detailing `original_story_id` and `new_story_id`.
- `StoryImpactScoreUpdated`: Emitted when the decay algorithm recalculates the story's impact score.
