"use client";

import React, { ReactNode } from "react";
import { m, useReducedMotion } from "framer-motion";

interface PageTurnTransitionProps {
  pathname: string;
  direction: "forward" | "backward";
  children: ReactNode;
}

// Premium page-turn easing — matches a physical page deceleration curve
const PAGE_TURN_EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];
const PAGE_TURN_DURATION = 0.8; // 800ms
const MAX_ROTATION = 120; // degrees — sweet spot for magazine illusion without backface artifacts

export const PageTurnTransition = React.forwardRef<HTMLDivElement, PageTurnTransitionProps>(
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

  const isForward = direction === "forward";

  // Forward (Home → Topics): spine on right, page turns left-to-right
  // Backward (Topics → Home): spine on left, page turns right-to-left
  const exitRotateY = isForward ? -MAX_ROTATION : MAX_ROTATION;
  const transformOrigin = isForward ? "right center" : "left center";

  return (
    <m.div
      ref={ref}
      initial="initial"
      animate="animate"
      exit="exit"
      variants={{
        initial: {
          opacity: 0,
          rotateY: 0,
          scale: 0.97,
          zIndex: 10,
          transformPerspective: 2000,
        },
        animate: {
          opacity: 1,
          rotateY: 0,
          scale: 1,
          zIndex: 20,
          transformPerspective: 2000,
          transition: {
            duration: PAGE_TURN_DURATION,
            ease: PAGE_TURN_EASE,
          },
          transitionEnd: { transform: "none" },
        },
        exit: {
          // Hold opacity at 1 until 70% through, then fade to hide backface
          opacity: [1, 1, 1, 0],
          rotateY: exitRotateY,
          zIndex: 30,
          transformPerspective: 2000,
          transition: {
            rotateY: { duration: PAGE_TURN_DURATION, ease: PAGE_TURN_EASE },
            opacity: {
              duration: PAGE_TURN_DURATION,
              times: [0, 0.5, 0.7, 1],
              ease: PAGE_TURN_EASE,
            },
          },
        },
      }}
      style={{
        transformOrigin,
        backfaceVisibility: "hidden",
        WebkitBackfaceVisibility: "hidden",
        transformStyle: "preserve-3d",
        willChange: "transform, opacity",
      }}
      className="w-full min-h-screen flex flex-col bg-background relative"
    >
      {/* === Spine edge highlight — simulates light catching the page edge === */}
      <m.div
        variants={{
          initial: { opacity: 0 },
          animate: { opacity: 0, transition: { duration: 0.3 } },
          exit: {
            opacity: [0, 0.6, 0.8, 0],
            transition: {
              duration: PAGE_TURN_DURATION,
              times: [0, 0.3, 0.7, 1],
              ease: PAGE_TURN_EASE,
            },
          },
        }}
        className="absolute top-0 bottom-0 pointer-events-none z-50"
        style={{
          width: "3px",
          ...(isForward
            ? {
                right: 0,
                background:
                  "linear-gradient(to left, rgba(255,255,255,0.35), transparent)",
              }
            : {
                left: 0,
                background:
                  "linear-gradient(to right, rgba(255,255,255,0.35), transparent)",
              }),
        }}
      />

      {/* === Page thickness illusion — thin strip along spine edge === */}
      <m.div
        variants={{
          initial: { opacity: 0 },
          animate: { opacity: 0 },
          exit: {
            opacity: [0, 0.3, 0.5, 0],
            transition: {
              duration: PAGE_TURN_DURATION,
              times: [0, 0.2, 0.6, 1],
              ease: PAGE_TURN_EASE,
            },
          },
        }}
        className="absolute top-0 bottom-0 pointer-events-none z-50"
        style={{
          width: "1.5px",
          ...(isForward
            ? {
                right: "3px",
                background:
                  "linear-gradient(to bottom, rgba(255,255,255,0.1) 10%, rgba(255,255,255,0.2) 50%, rgba(255,255,255,0.1) 90%)",
              }
            : {
                left: "3px",
                background:
                  "linear-gradient(to bottom, rgba(255,255,255,0.1) 10%, rgba(255,255,255,0.2) 50%, rgba(255,255,255,0.1) 90%)",
              }),
        }}
      />

      {/* === Page content === */}
      <div className="w-full flex-1">{children}</div>

      {/* === Dynamic shadow overlay — darkens as page lifts away === */}
      <m.div
        variants={{
          initial: { opacity: 0.4 },
          animate: {
            opacity: 0,
            transition: { duration: PAGE_TURN_DURATION, ease: PAGE_TURN_EASE },
          },
          exit: {
            opacity: [0, 0.15, 0.35, 0.5],
            transition: {
              duration: PAGE_TURN_DURATION,
              times: [0, 0.2, 0.5, 1],
              ease: PAGE_TURN_EASE,
            },
          },
        }}
        className="absolute inset-0 pointer-events-none z-40"
        style={{
          // Shadow gradient emanates from the spine edge
          background: isForward
            ? "linear-gradient(to left, transparent 0%, rgba(0,0,0,0.12) 40%, rgba(0,0,0,0.25) 100%)"
            : "linear-gradient(to right, transparent 0%, rgba(0,0,0,0.12) 40%, rgba(0,0,0,0.25) 100%)",
        }}
      />

      {/* === Cast shadow beneath the turning page === */}
      <m.div
        variants={{
          initial: { opacity: 0 },
          animate: { opacity: 0 },
          exit: {
            opacity: [0, 0.3, 0.6, 0],
            transition: {
              duration: PAGE_TURN_DURATION,
              times: [0, 0.2, 0.7, 1],
              ease: PAGE_TURN_EASE,
            },
          },
        }}
        className="absolute pointer-events-none z-[9]"
        style={{
          top: "2%",
          bottom: "2%",
          width: "60%",
          ...(isForward
            ? { left: "10%", transform: "skewY(-2deg)" }
            : { right: "10%", transform: "skewY(2deg)" }),
          background: "radial-gradient(ellipse at center, rgba(0,0,0,0.18) 0%, transparent 70%)",
          filter: "blur(20px)",
        }}
      />
    </m.div>
  );
});
