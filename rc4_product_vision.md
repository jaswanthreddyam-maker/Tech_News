# RC4 — Editorial Experience Platform

**Vision**: Translate the foundational architecture and editorial intelligence built in RC3 into visible, premium user-facing product capabilities powered by a composable Document Presentation System.

---

## Strategic Layering Architecture

```text
Backend Business Intelligence (DocumentType Enum, is_multi_topic, primary_topics)
                        │
                        ▼
      Layer 1: Document Presentation System (`src/domains/article/presentation/`)
      getPresentationForArticle(article) -> Composable PresentationConfig
                        │
       ┌────────────────┼────────────────┬────────────────┐
       ▼                ▼                ▼                ▼
Workstream A       Workstream B     Workstream C     Workstream D
Presentation System Adaptive Cards   Intelligence UI  Reading Experience
(Strategy Module)  (Card Layouts)   (Topic Recs/Filters) (Immersive Reader)
```

---

## Component Isolation Rule
**No UI component shall inspect `article.documentType` directly via conditional string checks (`if (docType === "newsletter")`).**  
Instead, all components consume the composable `PresentationConfig` produced by `getPresentationForArticle(article)` or `getPresentationConfig(docType, isMultiTopic)`:

```tsx
const presentation = getPresentationForArticle(article);

<Card presentation={presentation} />
```

---

## Composable `PresentationConfig` Schema

```ts
export interface PresentationConfig {
  documentType: string;
  badge: {
    label: string;
    icon: string;
    className: string;
  };
  accent: "neutral" | "breaking" | "opinion" | "review" | "newsletter" | "roundup" | "live" | "explainer";
  cardVariant: "standard" | "collection" | "breaking" | "review" | "opinion" | "live";
  animation: "standard" | "urgent" | "subtle" | "none";
  interaction: "standard" | "elevate" | "expand";
  metadata: {
    showTopics: boolean;
    showUrgency: boolean;
    showReadingTime: boolean;
    showAuthorByline: boolean;
  };
}
```

---

## Implementation Sprint Order

- **Sprint 1 (Workstream A)**: Document Presentation System Foundation (Completed).
- **Sprint 2 (Workstream B)**: Adaptive Story Cards (`presentation.cardVariant`).
- **Sprint 3 (Workstream C)**: Document Type Badges & Intelligence Filters.
- **Sprint 4 (Workstream C)**: Topic-Overlap Recommendation Engine (`primaryTopics`).
- **Sprint 5 (Workstream D)**: Immersive Reading Experience Platform.
