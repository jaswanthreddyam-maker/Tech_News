# News Impact Scoring Design

## Context
As part of the RC3.1 Editorial Intelligence Foundations, we are introducing the capability to measure "News Impact Scoring."
Instead of hardcoding a final algorithm today, this document establishes the *design and methodology* for impact scoring. The actual scoring logic will be refined and certified based on production telemetry and editorial feedback.

## Goal
Determine article relevance, persistence, and retirement eligibility using purely internal telemetry.

## Guiding Principles
1. **Internal Telemetry Only**: Do not rely on external social media metrics or trending APIs.
2. **Story-Centric**: Impact is measured not just per article, but across the entire `Story` domain. A high-impact story keeps its constituent articles relevant longer.
3. **Decay is Natural**: All news decays. The score must incorporate a half-life function.
4. **Observable**: Every component of the score must be transparent and reconstructable (Explainability Over Magic).

## Inputs (Internal Telemetry)
The scoring algorithm will ingest the following signals from the `ArticleMetrics` and `UserReadingHistory` systems:
- `total_views`: Base traffic.
- `average_read_time_seconds`: Indicator of deep engagement vs. clickbait.
- `click_through_rate` (CTR): Relevancy from the homepage.
- `bookmarks_count`: Strong signal of high enduring value.
- `newsletter_clicks`: Directed engagement from high-intent subscribers.

## Proposed Formula Structure
The Impact Score (`I`) at time `t` will be a function of Base Engagement (`E`) multiplied by a Time Decay factor (`D`).

`I(t) = E * D(t)`

### Base Engagement (E)
A weighted sum of engagement signals:
`E = (w1 * normalized_views) + (w2 * normalized_read_time) + (w3 * bookmarks) + (w4 * newsletter_clicks)`

*Initial weight hypotheses to be tested:*
- `w1` (Views): 1.0
- `w2` (Read Time): 2.5
- `w3` (Bookmarks): 5.0
- `w4` (Newsletter): 3.0

### Time Decay Factor (D)
An exponential decay function based on the article's age and its `Story` momentum.
`D(t) = e^(-λ * t)`
where `λ` is the decay constant, dynamically adjusted by the overarching `Story` impact. A breaking, highly followed story has a smaller `λ`, preserving its impact score longer.

## State Transitions
When a Story's Impact Score drops below a configured threshold, it becomes eligible for retirement.
- `StoryStatus.ACTIVE` -> `StoryStatus.DORMANT`
- `StoryStatus.DORMANT` -> `StoryStatus.ARCHIVED`

(Individual articles follow their own publication lifecycle, but their long-term visibility on the homepage is driven by their parent Story's impact score).

## Next Steps
During the remainder of the RC3 lifecycle:
1. Gather production telemetry on the new engagement metrics.
2. Simulate the proposed formula against historical data.
3. Establish the final weighting and decay constants.
4. Certify the algorithm against editorial expectations.
5. Implement the scoring engine to actively update the `Story.impact_score` field.
