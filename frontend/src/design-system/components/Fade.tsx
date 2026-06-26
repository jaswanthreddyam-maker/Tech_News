// design-system/components/Fade.tsx
"use client";

import React from "react";
import { m, HTMLMotionProps, Variants } from "framer-motion";
import { useAppReducedMotion } from "../accessibility/reducedMotion";

export interface FadeProps extends HTMLMotionProps<"div"> {
  children: React.ReactNode;
  delay?: number;
  width?: "fit-content" | "100%";
}

export function Fade({ children, delay = 0, width = "fit-content", ...rest }: FadeProps) {
  const shouldReduceMotion = useAppReducedMotion();

  const variants: Variants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        duration: shouldReduceMotion ? 0.15 : 0.4,
        ease: "linear",
        delay,
      },
    },
  };

  return (
    <m.div
      style={{ width }}
      variants={variants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-50px" }}
      {...rest}
    >
      {children}
    </m.div>
  );
}
