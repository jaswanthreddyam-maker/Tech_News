// design-system/motion/variants.ts
// ─── Reusable motion presets ───────────────────────────────────────
// Every animation in the app is composed from these presets.
// Keeps visual language consistent; no ad-hoc values scattered in components.

import { Variants } from "framer-motion";
import { DURATION, EASING } from "./tokens";

const ease = EASING.standard;
const exitEase = EASING.exit;

// ── Entrance presets ──────────────────────────────────────────────

/** Fade up — general purpose entrance (sidebar items, controls) */
export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: DURATION.normal, ease } },
  exit:    { opacity: 0, y: 8,  transition: { duration: DURATION.fast,   ease: exitEase } },
};

/** Fade right — slides in from left (floating toolbar) */
export const fadeRight: Variants = {
  hidden: { opacity: 0, x: -30 },
  visible: { opacity: 1, x: 0, transition: { duration: DURATION.normal, ease } },
  exit:    { opacity: 0, x: -16, transition: { duration: DURATION.fast, ease: exitEase } },
};

/** Headline — blur + translate, no scale (text never scales) */
export const headlineReveal: Variants = {
  hidden: { opacity: 0, y: 20, filter: "blur(8px)" },
  visible: {
    opacity: 1, y: 0, filter: "blur(0px)",
    transition: { duration: DURATION.slow, ease },
  },
};

/** Hero clip-path wipe — vertical reveal from top, no blur on large image */
export const heroReveal: Variants = {
  hidden: { opacity: 0, clipPath: "inset(100% 0 0 0)" },
  visible: {
    opacity: 1, clipPath: "inset(0% 0 0 0)",
    transition: { duration: DURATION.page, ease },
  },
};

/** Sidebar — slides in as single unit from right */
export const sidebarReveal: Variants = {
  hidden: { opacity: 0, x: 30 },
  visible: {
    opacity: 1, x: 0,
    transition: { duration: DURATION.normal, ease },
  },
};

/** Page transition — entire article container (translateY only, no scale) */
export const pageTransition: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: {
    opacity: 1, y: 0,
    transition: { duration: DURATION.page, ease },
  },
  exit: {
    opacity: 0, y: -4,
    transition: { duration: DURATION.normal, ease: exitEase },
  },
};

/** Shared element ghost — thumbnail to hero */
export const sharedElement: Variants = {
  hidden: { opacity: 0, scale: 0.9 },
  visible: {
    opacity: 1, scale: 1,
    transition: { duration: DURATION.page, ease },
  },
  exit: {
    opacity: 0, scale: 0.95,
    transition: { duration: DURATION.fast, ease: exitEase },
  },
};

/** Block-level reveal — H2, blockquote, figure, pre entering viewport */
export const revealBlock: Variants = {
  hidden: { opacity: 0, y: 15 },
  visible: {
    opacity: 1, y: 0,
    transition: { duration: DURATION.normal, ease },
  },
};

// ── Lightbox presets ──────────────────────────────────────────────

/** Lightbox backdrop */
export const lightboxBackdrop: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: DURATION.fast } },
  exit:    { opacity: 0, transition: { duration: DURATION.fast } },
};

/** Lightbox image — scales from current position to center */
export const lightboxImage: Variants = {
  hidden: { opacity: 0, scale: 0.85 },
  visible: { opacity: 1, scale: 1, transition: { duration: DURATION.normal, ease } },
  exit:    { opacity: 0, scale: 0.9, transition: { duration: DURATION.fast } },
};

// ── Stagger container presets ─────────────────────────────────────

/** Container that staggers its children (toolbar icons, related cards) */
export const staggerContainer = (staggerChildren = 0.04, delayChildren = 0): Variants => ({
  hidden: {},
  visible: {
    transition: { staggerChildren, delayChildren },
  },
});

/** Stagger item — used inside staggerContainer */
export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0, transition: { duration: DURATION.fast, ease } },
};

// ── Hover / press microinteractions ──────────────────────────────
// Keep under 200ms — these are P5 micro interactions

export const hoverLift = {
  y: -2,
  transition: { duration: DURATION.micro, ease: EASING.decelerate },
};

export const pressScale = {
  scale: 0.97,
  transition: { duration: DURATION.micro },
};

// ── Legacy exports (kept for backward compat) ─────────────────────
export const fadeRevealVariants: Variants = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0, transition: { duration: DURATION.normal, ease } },
};

export const modalVariants: Variants = {
  hidden: { opacity: 0, scale: 0.95, y: 20 },
  visible: { opacity: 1, scale: 1, y: 0, transition: { duration: DURATION.normal, ease } },
  exit:    { opacity: 0, scale: 0.95, y: 20, transition: { duration: DURATION.fast } },
};
