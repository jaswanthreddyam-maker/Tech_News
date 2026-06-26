// design-system/components/Scale.tsx
"use client";

import React from "react";
import { m, HTMLMotionProps } from "framer-motion";
import { MotionTokens } from "../motion/tokens";
import { useAppReducedMotion, getReducedVariants } from "../accessibility/reducedMotion";

export interface ScaleProps extends HTMLMotionProps<"div"> {
  children: React.ReactNode;
  delay?: number;
  width?: "fit-content" | "100%";
}

export function Scale({ children, delay = 0, width = "fit-content", ...rest }: ScaleProps) {
  const shouldReduceMotion = useAppReducedMotion();

  const baseVariants = {
    hidden: { opacity: 0, scale: 0.95 },
    visible: {
      opacity: 1,
      scale: 1,
      transition: MotionTokens.reveal,
    },
  };

  const variants = getReducedVariants(baseVariants, shouldReduceMotion);
  
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
