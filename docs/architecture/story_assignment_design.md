# Story Assignment and Duplicate Detection Design

This document serves as the governance specification for the duplicate detection and story assignment engine introduced in RC3.2. It ensures that the transition from independent articles to narrative structures (`Stories`) remains deterministic, transparent, and auditable.

## 1. Core Philosophy

- **Explainability Over Magic**: Every automated assignment decision must be logged with the exact parameters that triggered it.
- **False Positives > False Negatives**: We strongly prefer creating a duplicate story (false negative assignment) over merging two unrelated events into the same story (false positive assignment). A bad merge pollutes the timeline, whereas a duplicate story can be manually merged later.
- **No Automatic Merges**: Stories can only be merged via explicit editorial action.

## 2. Similarity Thresholds

Incoming articles are evaluated against the centroid embeddings of `ACTIVE` and `DORMANT` stories. The cosine similarity score dictates the assignment action:

| Range | Decision | Action |
|-------|----------|--------|
| `>= 0.90` | `AUTO_ASSIGN` | The article is automatically appended to the highest-scoring candidate story. |
| `0.80 - 0.89` | `EDITOR_REVIEW` | The article is held in the Review Queue. It is not appended to the candidate story until approved by an editor. |
| `< 0.80` | `NEW_STORY` | The article does not match any existing narrative and automatically generates a new `StoryCreated` event. |

## 3. Assignment Decisions Audit Log

To preserve explainability, every ingestion evaluation generates a `StoryAssignmentDecision` record, regardless of the outcome:

```python
class StoryAssignmentDecision(Base):
    id: str                 # UUID
    article_id: str         # The incoming article
    candidate_story_id: str # The highest scoring story (if any)
    similarity_score: float # e.g., 0.912
    threshold_used: float   # e.g., 0.90
    decision: str           # 'AUTO_ASSIGN', 'EDITOR_REVIEW', or 'NEW_STORY'
    model_version: str      # e.g., 'text-embedding-3-small'
    decided_at: datetime    # Timestamp
```

## 4. Review Queue Rules

When an article falls into the `EDITOR_REVIEW` band (`0.80 - 0.89`), it is placed in a dedicated queue in the Editorial Dashboard.
- **Approve**: Appends the article to the candidate story.
- **Reject**: Forces the creation of a new story.
- **Timeout**: If no action is taken within 24 hours, the system defaults to `NEW_STORY` to prevent pipeline blocking (adhering to the "False Positives > False Negatives" principle).

## 5. Dormant Story Matching and Follow-Ups

The matching engine searches both `ACTIVE` and `DORMANT` stories.
- If a new article matches a `DORMANT` story with a score `>= 0.90`, the article is appended to the story, and a `StoryReawakened` event is emitted. The story status reverts to `ACTIVE`.
- If the score falls in the `0.80 - 0.89` band for a `DORMANT` story, the system emits a `FollowUpSuggested` event to notify editors of a potential continuation.

## 6. False Positive Handling

If an article is incorrectly assigned (`AUTO_ASSIGN`), the editorial team must be able to detach it.
- **Detachment Action**: Editors can detach an article from a story.
- **Event**: Emits an `ArticleDetachedFromStory` event.
- **Recalibration**: The system re-computes the story's centroid embedding without the offending article to prevent future mis-assignments.
