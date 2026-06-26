"use client";

import React, { useState, useEffect } from "react";
import { m, useReducedMotion, HTMLMotionProps } from "framer-motion";

interface StaggerContainerProps extends HTMLMotionProps<"div"> {
  children: React.ReactNode;
}

export function StaggerContainer({ children, className, ...props }: StaggerContainerProps) {
  const [isMounted, setIsMounted] = useState(false);
  const shouldReduceMotion = useReducedMotion();

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const containerVariants = {
    hidden: {},
    visible: {
      transition: {
        delayChildren: shouldReduceMotion ? 0 : 0.12,
        staggerChildren: shouldReduceMotion ? 0 : 0.08,
      },
    },
  };

  if (!isMounted) {
    const { initial, animate, exit, transition, variants, whileInView, viewport, ...divProps } = props as any;
    return (
      <div className={className} {...divProps}>
        {children}
      </div>
    );
  }

  return (
    <m.div
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.2 }}
      variants={containerVariants}
      className={className}
      {...props}
    >
      {children}
    </m.div>
  );
}

interface StaggerItemProps extends HTMLMotionProps<"div"> {
  children: React.ReactNode;
}

export function StaggerItem({ children, className, ...props }: StaggerItemProps) {
  const [isMounted, setIsMounted] = useState(false);
  const shouldReduceMotion = useReducedMotion();

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const itemVariants = {
    hidden: shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 30, scale: 0.98 },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        duration: shouldReduceMotion ? 0.15 : 0.5,
        ease: (shouldReduceMotion ? "linear" : [0.22, 1, 0.36, 1]) as any,
      },
    },
  };

  if (!isMounted) {
    const { initial, animate, exit, transition, variants, whileHover, whileTap, whileInView, viewport, ...divProps } = props as any;
    return (
      <div className={className} {...divProps}>
        {children}
      </div>
    );
  }

  return (
    <m.div
      variants={itemVariants}
      className={className}
      {...props}
    >
      {children}
    </m.div>
  );
}
