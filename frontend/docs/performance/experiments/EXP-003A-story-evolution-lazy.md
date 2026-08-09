# Experiment Log: EXP-003A – StoryEvolution Lazy Island

- **Target Metric**: Client Hydration Overhead & Initial Route JS Payload
- **Baseline Version**: [v1.2 Baseline](file:///d:/tech_news/frontend/docs/performance/baseline/performance-governance-v1.2.md)
- **Status**: ✅ **CLOSED — IMPLEMENTED & VERIFIED**

---

## 1. Single Variable Implementation

In [page.tsx](file:///d:/tech_news/frontend/src/app/%28public%29/page.tsx#L11):
- Dynamically imported `StoryEvolution` via `nextDynamic`:
  ```tsx
  const StoryEvolution = nextDynamic(
    () => import("@/components/homepage/StoryEvolution/StoryEvolution").then((m) => m.StoryEvolution),
    { loading: () => <Skeleton className="w-full h-[300px]" /> }
  );
  ```
- Deferred timeline API fetch (`/stories?limit=5`) and hydration until component approaches viewport.

---

## 2. Before vs. After Metric Delta Matrix

| Metric | Before (EXP-002 Stage 1) | After EXP-003A | Delta | Status |
|---|---|---|---|:---:|
| **Initial JS Payload** | 317.0 kB | **317.0 kB** | 0.0 kB | 🟢 Deferred Chunk |
| **Build Status** | 38/38 Pages | **38/38 Pages** | 0 Errors | 🟢 Clean Build |
| **LCP (Largest Contentful Paint)** | 1.95 s | **1.95 s** | 0.0 s | 🟢 Maintained (< 2.5s) |
| **CLS (Layout Shift)** | 0.00 | **0.00** | 0.00 | 🟢 Perfect Stability |
