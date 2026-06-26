// design-system/components/Stagger.tsx
"use client";

import React from "react";
import { m, HTMLMotionProps } from "framer-motion";
import { useAppReducedMotion } from "../accessibility/reducedMotion";

export interface StaggerProps extends HTMLMotionProps<"div"> {
  children: React.ReactNode;
  staggerChildren?: number;
  delayChildren?: number;
  width?: "fit-content" | "100%";
}

export function Stagger({
  children,
  staggerChildren = 0.1,
  delayChildren = 0,
  width = "100%",
  ...rest
}: StaggerProps) {
  const shouldReduceMotion = useAppReducedMotion();

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: shouldReduceMotion ? 0 : staggerChildren,
        delayChildren: shouldReduceMotion ? 0 : delayChildren,
      },
    },
  };

  return (
    <m.div
      style={{ width }}
      variants={containerVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-50px" }}
      {...rest}
    >
      {children}
    </m.div>
  );
}
