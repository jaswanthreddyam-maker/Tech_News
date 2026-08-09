/* eslint-disable @next/next/no-img-element */
"use client";

import React, { ReactNode, useEffect, useState } from "react";
import { m, useReducedMotion } from "framer-motion";
import { DURATION, EASING } from "@/design-system/motion/tokens";

interface ArticlePeelTransitionProps {
  pathname: string;
  direction: "open" | "close";
  cardRect?: DOMRect | null;
  cardImageSrc?: string | null;
  cardTitle?: string | null;
  children: ReactNode;
}

const ease = EASING.standard;

/**
 * ArticlePeelTransition
 *
 * Card-expand transition: article page enters from the card's position.
 * No 3D peel, no rotateX, no page scale (causes text rasterization).
 *
 * Animation:
 * - Homepage exit: opacity 1 → 0.96 (barely perceptible — no white flash)
 * - Article enter: opacity+translateY from card origin, 450ms easeInOut
 * - Back navigation: article compresses, homepage returns
 *
 * Reduced motion: simple crossfade 150ms only.
 */
export const ArticlePeelTransition = React.forwardRef<
  HTMLDivElement,
  ArticlePeelTransitionProps
>(({ pathname, direction, cardRect, cardImageSrc, cardTitle, children }, ref) => {
  const shouldReduceMotion = useReducedMotion();
  const isHome = pathname === "/" || pathname === "/topics";
  const isOpen = direction === "open";

  // Reduced motion: pure crossfade, 150ms, nothing else moves
  if (shouldReduceMotion) {
    return (
      <m.div
        ref={ref}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15, ease: "linear" }}
        className="w-full min-h-screen flex flex-col"
      >
        {children}
      </m.div>
    );
  }

  // ─── Homepage layer ─────────────────────────────────────────────
  if (isHome) {
    return (
      <m.div
        ref={ref}
        key={pathname}
        initial={{ opacity: isOpen ? 1 : 0 }}
        animate={{ opacity: 1 }}
        exit={
          isOpen
            ? {
                // Opening article: homepage fades very slightly (no white flash)
                opacity: 0.96,
                transition: { duration: DURATION.page, ease },
              }
            : {
                // This variant unused when homepage exits — article-close uses article layer
                opacity: 0,
                transition: { duration: DURATION.normal, ease },
              }
        }
        transition={{ duration: DURATION.page, ease }}
        className="w-full min-h-screen flex flex-col bg-background relative"
      >
        {children}
      </m.div>
    );
  }

  // ─── Article layer ──────────────────────────────────────────────
  // Enters from card position (if cardRect available) or simple fadeUp
  return (
    <m.div
      ref={ref}
      key={pathname}
      initial={{
        opacity: 0,
        y: isOpen ? 8 : -4, // Open: comes up; Close: goes down
      }}
      animate={{
        opacity: 1,
        y: 0,
        transition: {
          duration: DURATION.page,
          ease,
          delay: isOpen ? 0.05 : 0,
        },
      }}
      exit={{
        opacity: 0,
        y: isOpen ? -4 : 8,
        transition: {
          duration: DURATION.normal,
          ease: EASING.exit,
        },
      }}
      style={{
        willChange: "opacity, transform",
      }}
      className="w-full min-h-screen flex flex-col bg-background relative"
    >
      {/* Shared element: thumbnail → hero (ghost overlay) */}
      {isOpen && cardImageSrc && cardRect && (
        <SharedImageGhost
          imageSrc={cardImageSrc}
          cardRect={cardRect}
        />
      )}
      {children}
    </m.div>
  );
});

ArticlePeelTransition.displayName = "ArticlePeelTransition";

// ---------------------------------------------------------------------------
// SharedImageGhost
// A ghost image that expands from the card's screen position.
// Positioned absolutely over the article, plays once then vanishes.
// ---------------------------------------------------------------------------
interface SharedImageGhostProps {
  imageSrc: string;
  cardRect: DOMRect;
}

function SharedImageGhost({ imageSrc, cardRect }: SharedImageGhostProps) {
  const [visible, setVisible] = useState(true);
  const [windowWidth, setWindowWidth] = useState<number>(1200);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setWindowWidth(window.innerWidth);

      const handleResize = () => setWindowWidth(window.innerWidth);
      window.addEventListener("resize", handleResize);

      const t = setTimeout(() => setVisible(false), 600);
      return () => {
        window.removeEventListener("resize", handleResize);
        clearTimeout(t);
      };
    }
  }, []);

  if (!visible) return null;

  const heroTop = 80; // px — approximate hero image top (below navbar)
  const heroWidth = Math.min(windowWidth - 32, 900); // max hero width
  const heroHeight = Math.round(heroWidth * 0.45); // ~450px at full width
  const heroLeft = Math.max(16, (windowWidth - heroWidth) / 2);

  return (
    <m.div
      initial={{
        position: "fixed",
        top: cardRect.top,
        left: cardRect.left,
        width: cardRect.width,
        height: cardRect.height,
        opacity: 1,
        borderRadius: "0.75rem",
        zIndex: 50,
        overflow: "hidden",
      }}
      animate={{
        top: heroTop,
        left: heroLeft,
        width: heroWidth,
        height: heroHeight,
        opacity: 0,
        borderRadius: "0.75rem",
      }}
      transition={{ duration: 0.45, ease: EASING.standard }}
      style={{ pointerEvents: "none" }}
    >
      <img
        src={imageSrc}
        alt=""
        aria-hidden="true"
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />
    </m.div>
  );
}

