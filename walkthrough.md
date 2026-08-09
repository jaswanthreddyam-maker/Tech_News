# Performance Execution Walkthrough — EXP-003B & Module-Level Bundle Audit

Following the **[Performance Governance Baseline v1.2](file:///d:/tech_news/frontend/docs/performance/baseline/performance-governance-v1.2.md)** protocol, **EXP-003B** and the **Module-Level Bundle Ownership Audit** are complete.

---

## 1. EXP-003B Single Variable Implementation ([page.tsx](file:///d:/tech_news/frontend/src/app/%28public%29/page.tsx#L18))

Converted `RelatedStories` to a scroll-deferred dynamic island using `nextDynamic`:
```tsx
const RelatedStories = nextDynamic(
  () => import("@/components/homepage/RelatedStories/RelatedStories").then((m) => m.RelatedStories),
  { loading: () => <Skeleton className="w-full h-[600px]" /> }
);
```

---

## 2. Empirical Module-Level Bundle Ownership Audit (`@next/bundle-analyzer`)

Captured client treemap report via `ANALYZE=true npm run build`:

| Module Name | Uncompressed Stat Size | Primary Purpose | Needed on Initial Homepage Route? |
|---|---|---|:---:|
| **`react-markdown` + `micromark`** | **599.4 KB** | Markdown parser for article reader | ❌ No (Article Reader only) |
| **`framer-motion` + `motion-dom`** | **507.7 KB** | Animations & gesture tracking | ⚠️ Partial (Hero only) |
| **`zod`** | **265.1 KB** | Schema validation for forms/API | ❌ No (Form/Admin pages only) |
| **`@radix-ui/*`** | **131.3 KB** | Primitive UI dropdowns/selects | ⚠️ Partial |
| **`date-fns`** | **84.1 KB** | Date formatting helper utilities | ⚠️ Partial (Relative dates) |
| **`@tanstack/react-virtual`** | **50.3 KB** | List virtualization | ⚠️ Partial |

---

## 3. High-ROI Targets Identified for PR-3

- **Target 1**: Defer `react-markdown` (599.4 KB) strictly to article reader pages.
- **Target 2**: Defer `zod` (265.1 KB) strictly to admin/auth form submission routes.
- **Target 3**: Constrain `framer-motion` (507.7 KB) using lightweight `domAnimation` features.

---

## Archived Experiment Artifacts
- **Experiment Log**: [EXP-003B-related-stories-lazy.md](file:///d:/tech_news/frontend/docs/performance/experiments/EXP-003B-related-stories-lazy.md)
- **Canonical Baseline**: [performance-governance-v1.2.md](file:///d:/tech_news/frontend/docs/performance/baseline/performance-governance-v1.2.md)
