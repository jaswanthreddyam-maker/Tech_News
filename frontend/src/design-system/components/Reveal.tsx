// design-system/components/Reveal.tsx
"use client";

import React from "react";
import { m, HTMLMotionProps } from "framer-motion";
import { fadeRevealVariants } from "../motion/variants";
import { useAppReducedMotion, getReducedVariants } from "../accessibility/reducedMotion";

export interface RevealProps extends HTMLMotionProps<"div"> {
  children: React.ReactNode;
  delay?: number;
  width?: "fit-content" | "100%";
}

export function Reveal({ children, delay = 0, width = "fit-content", ...rest }: RevealProps) {
  const shouldReduceMotion = useAppReducedMotion();
  const variants = getReducedVariants(fadeRevealVariants, shouldReduceMotion);

  // If delay is provided, override the variant transition delay
  const customVariants = {
    ...variants,
    visible: {
      ...variants.visible,
      transition: {
        ...(variants.visible as any).transition,
        delay,
      }
    }
  };

  return (
    <m.div
      style={{ width }}
      variants={customVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-50px" }}
      {...rest}
    >
      {children}
    </m.div>
  );
}
