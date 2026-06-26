"use client";

import React, { useState, useEffect } from "react";
import { m, useReducedMotion } from "framer-motion";

interface RevealProps {
  children: React.ReactNode;
  className?: string;
}

export function Reveal({ children, className }: RevealProps) {
  const [isMounted, setIsMounted] = useState(false);
  const shouldReduceMotion = useReducedMotion();

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const variants = {
    hidden: shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 50, scale: 0.98 },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        duration: shouldReduceMotion ? 0.15 : 0.7,
        ease: (shouldReduceMotion ? "linear" : [0.22, 1, 0.36, 1]) as any,
      },
    },
  };

  if (!isMounted) {
    return <div className={className}>{children}</div>;
  }

  return (
    <m.div
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.2 }}
      variants={variants}
      className={className}
    >
      {children}
    </m.div>
  );
}
