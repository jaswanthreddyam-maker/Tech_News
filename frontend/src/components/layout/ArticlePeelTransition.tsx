"use client";

import React, { ReactNode } from "react";
import { m, useReducedMotion } from "framer-motion";

interface ArticlePeelTransitionProps {
  pathname: string;
  direction: "open" | "close";
  cardRect?: DOMRect | null;
  children: ReactNode;
}

const PEEL_EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

export const ArticlePeelTransition = React.forwardRef<HTMLDivElement, ArticlePeelTransitionProps>(
  ({ pathname, direction, cardRect, children }, ref) => {
  const shouldReduceMotion = useReducedMotion();
  const isHome = pathname === "/";
  const isOpen = direction === "open";

  // Reduced motion: simple crossfade
  if (shouldReduceMotion) {
    return (
      <m.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15, ease: "easeInOut" }}
        className="w-full min-h-screen flex flex-col"
      >
        {children}
      </m.div>
    );
  }

  // ─────────────────────────────────────────────────────────
  // HOME LAYER — the newspaper front page that peels away
  // ─────────────────────────────────────────────────────────
  if (isHome) {
    return (
      <m.div
        ref={ref}
        initial="initial"
        animate="animate"
        exit="exit"
        variants={{
          // Entering (returning from article — homepage rises back)
          initial: {
            opacity: 0,
            rotateX: 25,
            translateY: "50%",
            zIndex: 10,
            transformPerspective: 2000,
          },
          animate: isOpen
            ? {
                // Opening article: homepage is already visible, just waiting
                opacity: 1,
                rotateX: 0,
                translateY: "0%",
                zIndex: 20,
                transformPerspective: 2000,
                transition: { duration: 0.6, ease: PEEL_EASE },
                transitionEnd: { transform: "none" },
              }
            : {
                // Closing article: homepage rises back with bounce
                // Stage 1: Rise from below (0→500ms)
                // Stage 2: Overshoot bounce: rotateX overshoots to -2° then settles (500→700ms)
                opacity: [0, 0.7, 1, 1, 1, 1],
                rotateX: [25, 8, 0, -2, 0.5, 0],
                translateY: ["50%", "10%", "0%", "0%", "0%", "0%"],
                zIndex: 20,
                transition: {
                  duration: 0.7,
                  times: [0, 0.35, 0.6, 0.78, 0.9, 1],
                  ease: PEEL_EASE,
                },
              },
          // Exiting (opening article — homepage peels away)
          exit: {
            // Stage 1 (0→25%): Slight forward tilt — "top still attached"
            // Stage 2 (25→100%): Bottom falls away, full peel
            rotateX: [0, 6, 20, 30],
            translateY: ["0%", "0%", "25%", "60%"],
            opacity: [1, 1, 0.85, 0],
            zIndex: 30,
            transformPerspective: 2000,
            transition: {
              duration: 0.8,
              times: [0, 0.2, 0.55, 1],
              ease: PEEL_EASE,
            },
          },
        }}
        style={{
          transformOrigin: "top center",
          backfaceVisibility: "hidden",
          WebkitBackfaceVisibility: "hidden",
          transformStyle: "preserve-3d",
          willChange: "transform, opacity",
        }}
        className="w-full min-h-screen flex flex-col bg-background relative"
      >
        {children}

        {/* === Cast shadow — intensifies as sheet lifts from surface === */}
        <m.div
          variants={{
            initial: { opacity: 0 },
            animate: {
              opacity: 0,
              transition: { duration: 0.3 },
            },
            exit: {
              opacity: [0, 0.1, 0.25, 0.4],
              transition: {
                duration: 0.8,
                times: [0, 0.15, 0.4, 1],
                ease: PEEL_EASE,
              },
            },
          }}
          className="absolute inset-0 pointer-events-none z-40"
          style={{
            background:
              "linear-gradient(to bottom, transparent 0%, rgba(0,0,0,0.06) 30%, rgba(0,0,0,0.2) 100%)",
          }}
        />

        {/* === Bottom edge shadow — peeling sheet casting shadow downward === */}
        <m.div
          variants={{
            initial: { opacity: 0 },
            animate: { opacity: 0 },
            exit: {
              opacity: [0, 0.2, 0.5, 0],
              scaleY: [1, 1.5, 2, 2.5],
              transition: {
                duration: 0.8,
                times: [0, 0.2, 0.6, 1],
                ease: PEEL_EASE,
              },
            },
          }}
          className="absolute left-[10%] right-[10%] bottom-0 h-8 pointer-events-none z-[9]"
          style={{
            background:
              "radial-gradient(ellipse at center bottom, rgba(0,0,0,0.2) 0%, transparent 80%)",
            filter: "blur(12px)",
            transformOrigin: "bottom center",
          }}
        />
      </m.div>
    );
  }

  // ─────────────────────────────────────────────────────────
  // ARTICLE LAYER — revealed beneath the peeling homepage
  // ─────────────────────────────────────────────────────────
  return (
    <m.div
      ref={ref}
      initial="initial"
      animate="animate"
      exit="exit"
      variants={{
        initial: {
          opacity: 0,
          scale: 0.98,
          translateY: 20,
          zIndex: 10,
          transformPerspective: 2000,
        },
        animate: {
          opacity: 1,
          scale: 1,
          translateY: 0,
          zIndex: 20,
          transformPerspective: 2000,
          transition: {
            duration: 0.7,
            ease: PEEL_EASE,
            // Slight delay so article reveals after peel starts
            delay: 0.1,
          },
          transitionEnd: { transform: "none" },
        },
        exit: {
          // Article compresses back when going home
          opacity: 0,
          scale: 0.97,
          zIndex: 10,
          transformPerspective: 2000,
          transition: {
            duration: 0.5,
            ease: "easeInOut",
          },
        },
      }}
      style={{
        transformStyle: "preserve-3d",
        backfaceVisibility: "hidden",
        WebkitBackfaceVisibility: "hidden",
        willChange: "transform, opacity",
      }}
      className="w-full min-h-screen flex flex-col bg-background relative"
    >
      {children}
    </m.div>
  );
});
