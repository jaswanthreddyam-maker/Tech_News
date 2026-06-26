# Editorial Intelligence Vision

## Overview
As Tech News Today transitions from infrastructure resilience (RC2) to domain intelligence (RC3), a clear definition of editorial concepts is required. This document establishes the shared language, definitions, and operational boundaries for the **Editorial Intelligence Layer**.

## Domain Definitions

### What is Editorial Intelligence?
Editorial Intelligence is the set of capabilities that surface insights, highlight gaps, and automate administrative lifecycle management of news content. It empowers human editors by removing rote categorization and scheduling burdens, allowing them to focus on narrative quality and investigative coverage. 

### Decision Boundaries

#### What decisions can be automated?
- **Lifecycle Transitions**: Archiving stories that have naturally decayed below the persistence threshold (e.g. 24-hour retirement).
- **Duplicate Prevention**: Rejecting or silently absorbing identical feeds to prevent newsroom clutter.
- **Contextual Graphing**: Linking related articles, identifying chronological evolution, and surfacing relevant historical context automatically.
- **Impact Measurement**: Scoring articles continuously based on real-time internal telemetry (views, reading time).

#### What decisions remain editorial?
- **Narrative Judgment**: Determining the nuance, tone, and accuracy of a story.
- **Overrides**: Manually pinning a highly important article that algorithms might discount, or instantly retiring a misleading piece.
- **Campaign Execution**: Approving and launching newsletters, breaking news alerts, and push notifications.
- **Follow-up Generation**: Deciding whether an evolving story warrants a newly written investigative piece or follow-up summary.

### Core Entities & Concepts

#### What is a Story?
A **Story** is a conceptual narrative arc, not a single article. A Story represents the overarching topic or event (e.g., "The OpenAI Board Shakeup"). An **Article** is a specific, point-in-time artifact describing one facet of that Story. The platform ingests Articles, but the Editorial Intelligence Layer constructs and monitors *Stories*.

#### What is Impact?
**Impact** is a continuously recalculating score representing the true relevance and engagement of an article within the ecosystem. It is explicitly decoupled from external hype (e.g., Twitter trends) and relies purely on deterministic internal telemetry:
- Page Views & Unique Readers
- Click-Through Rate (CTR)
- Active Reading Time
- Newsletter Clicks
- Publication Age (Freshness Decay)

#### What is Story Evolution?
**Story Evolution** is the chronological progression of a narrative. It is the ability to link consecutive Articles together into a cohesive timeline, showing how initial breaking news evolved into deep analysis, regulatory reaction, and market impact. 

#### What is Coverage?
**Coverage** represents the breadth and depth of the platform's reporting across all tracked entities, categories, and topics. "Coverage Monitoring" identifies blind spots—such as a high volume of user searches for a specific company with no corresponding active Articles—prompting the newsroom to fill the gap.

#### What is Revisit Rate? (Post-RC3.3B Backlog)
**Revisit Rate** measures whether readers return to an ongoing story. Calculated as `returning_readers / unique_readers`, it shifts the analytical question from *"Did people read this story?"* to *"Do people come back to this story?"* This is a powerful future signal for evaluating long-term narrative engagement.
