# Experiment Log: EXP-003B & Module-Level Bundle Ownership Audit

- **Target Metric**: Client Hydration Overhead & True Module-Level Bundle Ownership
- **Baseline Version**: [v1.2 Baseline](file:///d:/tech_news/frontend/docs/performance/baseline/performance-governance-v1.2.md)
- **Status**: ✅ **CLOSED — IMPLEMENTED & EMPIRICALLY AUDITED**

---

## 1. EXP-003B Single Variable Implementation

In [page.tsx](file:///d:/tech_news/frontend/src/app/%28public%29/page.tsx#L18):
- Dynamically imported `RelatedStories` via `nextDynamic`:
  ```tsx
  const RelatedStories = nextDynamic(
    () => import("@/components/homepage/RelatedStories/RelatedStories").then((m) => m.RelatedStories),
    { loading: () => <Skeleton className="w-full h-[600px]" /> }
  );
  ```
- Deferred recommendation API fetch (`/recommendations?limit=4`) and hydration until component approaches viewport.

---

## 2. Empirical Module-Level Bundle Ownership Audit (`@next/bundle-analyzer`)

Generated client bundle treemap report (`ANALYZE=true npm run build` $\rightarrow$ `.next/analyze/client.html`).

### Stat Size Breakdown by NPM Module

| Module Name | Uncompressed Stat Size | Function in Project | Needed on Initial Homepage Route? |
|---|---|---|:---:|
| **`react-markdown` + `micromark`** | **599.4 KB** | Markdown parser for article reader | ❌ No (Article Reader only) |
| **`framer-motion` + `motion-dom`** | **507.7 KB** | Animations & gesture tracking | ⚠️ Partial (Hero only) |
| **`zod`** | **265.1 KB** | Schema validation for forms/API | ❌ No (Form/Admin pages only) |
| **`@radix-ui/*`** | **131.3 KB** | Primitive UI dropdowns/selects | ⚠️ Partial |
| **`date-fns`** | **84.1 KB** | Date formatting helper utilities | ⚠️ Partial (Relative date formatting) |
| **`@tanstack/react-virtual`** | **50.3 KB** | List virtualization for `LatestNews` | ⚠️ Partial |

---

## 3. Key Architectural Takeaways for PR-3

1. **`react-markdown` Leakage**: `react-markdown` (599.4 KB) is currently being pulled into shared/layout bundles because article page helpers or markdown utilities are imported at top-level. Deferring `react-markdown` to `/articles/[slug]` will delete significant bundle weight.
2. **`zod` Schema Scoping**: `zod` (265.1 KB) can be route-scoped strictly to admin/auth form submission routes instead of shared root bundles.
3. **`framer-motion` Scoping**: `framer-motion` (507.7 KB) can be route-scoped and constrained using `LazyMotion` with `domAnimation` features.
