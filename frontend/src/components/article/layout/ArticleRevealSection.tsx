"use client";

import React, { ReactNode } from "react";
import { m, useReducedMotion } from "framer-motion";
import { fadeUp } from "@/design-system/motion/variants";
import { useNavigationType } from "@/hooks/useNavigationType";
import { DURATION, EASING } from "@/design-system/motion/tokens";

interface ArticleRevealSectionProps {
  children: ReactNode;
  delay?: number;
  className?: string;
}

/**
 * ArticleRevealSection
 *
 * Wraps a layout slot with a staggered entrance animation.
 * Animation only plays on cold loads (direct URL / refresh).
 * On client-side navigation: renders children immediately.
 *
 * Usage:
 *   <ArticleRevealSection delay={REVEAL_DELAYS.hero}>
 *     {heroImageNode}
 *   </ArticleRevealSection>
 */
export function ArticleRevealSection({
  children,
  delay = 0,
  className,
}: ArticleRevealSectionProps) {
  const { isColdLoad } = useNavigationType();
  const shouldReduceMotion = useReducedMotion();

  // On client navigation or reduced motion: render immediately, no animation
  if (!isColdLoad || shouldReduceMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <m.div
      initial="hidden"
      animate="visible"
      variants={{
        hidden: { opacity: 0, y: 16 },
        visible: {
          opacity: 1,
          y: 0,
          transition: {
            duration: DURATION.normal,
            ease: EASING.standard as any,
            delay,
          },
        },
      }}
      className={className}
    >
      {children}
    </m.div>
  );
}
