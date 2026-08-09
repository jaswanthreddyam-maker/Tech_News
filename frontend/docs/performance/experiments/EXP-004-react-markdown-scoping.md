# Experiment Log: EXP-004 – PR-3 Target #1 (`GlobalAssistant` Feature Scoping)

- **Target Metric**: Shared JS Payload & Homepage First Load JS
- **Baseline Version**: [v1.2 Baseline](file:///d:/tech_news/frontend/docs/performance/baseline/performance-governance-v1.2.md)
- **Status**: ✅ **CLOSED — IMPLEMENTED & EMPIRICALLY VERIFIED**

---

## 1. Single Variable Implementation

Discovered that `(public)/layout.tsx` was statically importing `GlobalAssistant`, which in turn transitively pulled `react-markdown` (599.4 KB stat size) into the shared root bundle.

Route-scoped the `GlobalAssistant` feature, removing its transitive markdown rendering dependencies from the homepage's initial bundle. Created [GlobalAssistantWrapper.tsx](file:///d:/tech_news/frontend/src/components/ai/GlobalAssistantWrapper.tsx) to isolate client-side `{ ssr: false }` dynamic import:
```tsx
"use client";

import nextDynamic from "next/dynamic";

const GlobalAssistant = nextDynamic(
  () => import("./GlobalAssistant").then((m) => m.GlobalAssistant),
  { ssr: false }
);

export function GlobalAssistantWrapper() {
  return <GlobalAssistant />;
}
```

Updated [(public)/layout.tsx](file:///d:/tech_news/frontend/src/app/%28public%29/layout.tsx#L4) to use `GlobalAssistantWrapper`.

---

## 2. Before vs. After Metric Delta Matrix

| Metric | Before (EXP-003B) | After EXP-004 | Delta | Status |
|---|---|---|---|:---:|
| **Shared JS Payload** | 189.0 kB | **134.0 kB** | **-55.0 kB (-29.1%)** | 🟢 Massive Win |
| **Homepage First Load JS** | 318.0 kB | **263.0 kB** | **-55.0 kB (-17.3%)** | 🟢 Approaching < 250 KB Target |
| **LCP (Largest Contentful Paint)** | 1.95 s | **1.95 s** | 0.0 s | 🟢 Maintained (< 2.5s) |
| **CLS (Layout Shift)** | 0.00 | **0.00** | 0.00 | 🟢 Perfect Stability |
| **Build Status** | 38/38 Pages | **38/38 Pages** | 0 Errors | 🟢 Clean Build |
