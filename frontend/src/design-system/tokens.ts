/**
 * Editorial Design System — Tokens (RC1)
 * Single source of truth for Typography, Spacing, Surface, and Motion.
 */

// ── Typography Tokens ─────────────────────────────────────────────
export const TYPOGRAPHY = {
  DisplayXL: "text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight font-sans text-foreground",
  DisplayL: "text-2xl sm:text-3xl font-bold tracking-tight font-sans text-foreground",
  Title: "text-xl sm:text-2xl font-semibold tracking-tight font-sans text-foreground",
  Heading: "text-lg sm:text-xl font-semibold leading-snug font-sans text-foreground",
  Body: "text-sm sm:text-base leading-relaxed text-muted-foreground",
  Meta: "text-xs font-mono text-muted-foreground/70",
  Caption: "text-[11px] font-mono tracking-widest uppercase text-muted-foreground/60",
} as const;

// ── Semantic Spacing Tokens (Chapter Cadence) ─────────────────────
export const SPACING = {
  SECTION_GAP_XL: "mb-32", // 128px rhythm between major chapters
  SECTION_GAP_L: "mb-24",  // 96px rhythm
  SECTION_GAP_M: "mb-16",  // 64px rhythm
  SECTION_GAP_S: "mb-8",   // 32px inner block rhythm
} as const;

// ── Motion Tokens ─────────────────────────────────────────────────
export const MOTION_PRESETS = {
  SCENE_ENTRANCE: {
    initial: { opacity: 0, y: 80, scale: 0.985, filter: "blur(8px)" },
    whileInView: { opacity: 1, y: 0, scale: 1, filter: "blur(0px)" },
    viewport: { once: true, amount: 0.15 },
    transition: { duration: 1.0, ease: [0.16, 1, 0.3, 1] },
  },
  SCENE_EXIT: {
    opacity: 0,
    y: 30,
    transition: { duration: 0.4, ease: [0.4, 0, 1, 1] },
  },
  CARD_LIFT: {
    whileHover: { y: -4 },
    transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] },
  },
  CTA_ARROW: {
    transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] },
  },
} as const;
