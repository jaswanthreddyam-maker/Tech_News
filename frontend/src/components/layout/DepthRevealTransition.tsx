"use client";

import React, { ReactNode } from "react";
import { m, useReducedMotion } from "framer-motion";

interface DepthRevealTransitionProps {
  pathname: string;
  direction: "open" | "close";
  children: ReactNode;
}

const DEPTH_EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

/**
 * DepthRevealTransition — used for Topics ↔ Article navigation.
 *
 * Concept: Topics page pushes back into depth (scales down + fades),
 * while the article rises forward. Clean and modern — no paper peel
 * metaphor since Topics isn't a "newspaper front page".
 */
export const DepthRevealTransition = React.forwardRef<HTMLDivElement, DepthRevealTransitionProps>(
  ({ pathname, direction, children }, ref) => {
  const shouldReduceMotion = useReducedMotion();

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

  const isTopics = pathname === "/topics";
  const isOpen = direction === "open";

  // ─────────────────────────────────────────────────────────
  // TOPICS LAYER — scales back into depth
  // ─────────────────────────────────────────────────────────
  if (isTopics) {
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
            zIndex: 10,
            transformPerspective: 2000,
          },
          animate: isOpen
            ? {
                // Topics is already visible, stays put
                opacity: 1,
                scale: 1,
                zIndex: 20,
                transformPerspective: 2000,
                transition: { duration: 0.5, ease: DEPTH_EASE },
                transitionEnd: { transform: "none" },
              }
            : {
                // Returning from article: topics scales back up
                opacity: [0, 0.6, 1],
                scale: [0.98, 0.99, 1],
                zIndex: 20,
                transformPerspective: 2000,
                transition: {
                  duration: 0.5,
                  times: [0, 0.5, 1],
                  ease: DEPTH_EASE,
                },
                transitionEnd: { transform: "none" },
              },
          exit: {
            // Topics pushes into depth
            opacity: 0,
            scale: 0.98,
            zIndex: 10,
            transformPerspective: 2000,
            transition: {
              duration: 0.5,
              ease: DEPTH_EASE,
            },
          },
        }}
        style={{
          willChange: "transform, opacity",
        }}
        className="w-full min-h-screen flex flex-col bg-background relative"
      >
        {children}
      </m.div>
    );
  }

  // ─────────────────────────────────────────────────────────
  // ARTICLE LAYER — rises upward from depth
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
          translateY: 24,
          scale: 0.99,
          zIndex: 10,
          transformPerspective: 2000,
        },
        animate: {
          opacity: 1,
          translateY: 0,
          scale: 1,
          zIndex: 20,
          transformPerspective: 2000,
          transition: {
            duration: 0.6,
            ease: DEPTH_EASE,
            delay: 0.05,
          },
          transitionEnd: { transform: "none" },
        },
        exit: {
          // Article fades down when returning to topics
          opacity: 0,
          translateY: 16,
          scale: 0.99,
          zIndex: 10,
          transformPerspective: 2000,
          transition: {
            duration: 0.45,
            ease: "easeInOut",
          },
        },
      }}
      style={{
        willChange: "transform, opacity",
      }}
      className="w-full min-h-screen flex flex-col bg-background relative"
    >
      {children}
    </m.div>
  );
});
DepthRevealTransition.displayName = 'DepthRevealTransition';
