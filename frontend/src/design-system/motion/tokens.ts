// design-system/motion/tokens.ts
// ─── Single source of truth for all animation timing and easing ───
// Every animation in the app references this file.
// If timing needs global adjustment, change it here.

import { Transition } from "framer-motion";

// ── Easing curves ─────────────────────────────────────────────────
export const EASING = {
  /** Apple / Arc physical easing — used for full section scene reveals */
  cubicPhysical: [0.16, 1, 0.3, 1] as const,
  /** Smooth, natural easeInOut — used for page transitions */
  standard: [0.22, 1, 0.36, 1] as const,
  /** Snappy exit curve — content leaving faster than it enters */
  exit: [0.4, 0, 1, 1] as const,
  /** Gentle deceleration — sidebar, modals */
  decelerate: [0, 0, 0.2, 1] as const,
  /** Linear — reserved for progress bars, counters */
  linear: [0, 0, 1, 1] as const,
} as const;

/** RC3.1 Shared Section Scene Entrance Preset */
export const PHYSICAL_SCENE_ENTRANCE = {
  initial: { opacity: 0, y: 80, scale: 0.985, filter: "blur(8px)" },
  whileInView: { opacity: 1, y: 0, scale: 1, filter: "blur(0px)" },
  viewport: { once: true, amount: 0.15 },
  transition: { duration: 1.0, ease: [0.16, 1, 0.3, 1] },
} as const;

// ── Duration budget ───────────────────────────────────────────────
// Maximum 2 simultaneous large animations at any point.
export const DURATION = {
  /** Under 150ms — hover states, button presses, icon swaps */
  micro: 0.12,
  /** 150–250ms — tooltips, small UI state changes, theme switch */
  fast: 0.2,
  /** 250–400ms — modals, sidebars, reading mode switch */
  normal: 0.35,
  /** 400–500ms — page transitions, hero reveal */
  page: 0.45,
  /** 500–600ms — headline blur, hero clip-path */
  slow: 0.55,
} as const;

// ── Motion priority (for FPS budget awareness) ────────────────────
// When multiple animations compete, higher priorities win.
// Lower priorities defer or skip when performance is constrained.
export const MOTION_PRIORITY = {
  /** P1 — never skip */
  pageTransition: 1,
  /** P2 — hero image reveal */
  hero: 2,
  /** P3 — article headline */
  headline: 3,
  /** P4 — sidebar, toolbar */
  sidebar: 4,
  /** P5 — hover, press, link underlines */
  microinteraction: 5,
  /** P6 — viewport scroll reveals */
  viewportReveal: 6,
} as const;

// ── Stagger delays (ms → seconds for Framer) ─────────────────────
export const STAGGER = {
  /** Between sibling items (toolbar icons, related cards) */
  items: 0.04,
  /** Between major layout sections on first load */
  sections: 0.04,
} as const;

// ── Article page reveal order (seconds from page mount) ──────────
// Hero starts immediately — it occupies half the viewport.
// Max 2 large animations allowed at once (hero + headline).
export const REVEAL_DELAYS = {
  hero: 0.02,       // 20ms  — P2: hero begins before everything
  meta: 0.06,       // 60ms  — title + meta
  controls: 0.1,    // 100ms — reading mode controls
  sidebar: 0.14,    // 140ms — sidebar (one unit)
  body: 0.18,       // 180ms — article body
  toolbar: 0.06,    // 60ms  — floating toolbar (desktop only)
} as const;

// ── Legacy spring tokens (kept for backward compat) ───────────────
export const MotionTokens: Record<string, Transition> = {
  hover: { type: "spring", stiffness: 420, damping: 30, mass: 0.8 },
  reveal: { type: "spring", stiffness: 120, damping: 22, mass: 1 },
  modal: { type: "spring", stiffness: 300, damping: 28, mass: 0.9 },
};

export const MotionScales = {
  hover: 1.03,
  card: 1.015,
  tap: 0.97,
} as const;
