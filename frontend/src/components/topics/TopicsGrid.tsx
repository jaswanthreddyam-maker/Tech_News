"use client";

import React from "react";
import { m, useReducedMotion } from "framer-motion";

const containerVariants = {
  hidden: { opacity: 1 },
  show: {
    transition: {
      staggerChildren: 0.18, // delay between rows
      delayChildren: 0.1,
    },
  },
};

const rowVariants = {
  hidden: { opacity: 0, y: 24 },
  show: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: [0.22, 1, 0.36, 1] as any,
    },
  },
};

const cardVariants = {
  hidden: { opacity: 0, scale: 0.96 },
  show: {
    opacity: 1,
    scale: 1,
    transition: {
      duration: 0.35,
      ease: [0.22, 1, 0.36, 1] as any,
    },
  },
};

interface TopicsGridProps {
  rows: React.ReactNode[][];
  viewMode?: "grid" | "list";
}

export function TopicsGrid({ rows, viewMode = "grid" }: TopicsGridProps) {
  const shouldReduce = useReducedMotion();

  // Grid layout class based on viewMode
  const layoutClass = viewMode === "list" 
    ? "grid grid-cols-1 gap-6" 
    : "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6";

  if (shouldReduce) {
    return (
      <div className={layoutClass}>
        {rows.flat().map((card, i) => (
          <div key={i}>{card}</div>
        ))}
      </div>
    );
  }

  return (
    <m.div
      className={layoutClass}
      variants={containerVariants}
      initial="hidden"
      animate="show"
    >
      {rows.map((rowItems, rowIndex) => (
        <m.div key={rowIndex} className="contents" variants={rowVariants}>
          {rowItems.map((item, i) => (
            <m.div
              key={i}
              variants={cardVariants}
              className="h-full"
            >
              {item}
            </m.div>
          ))}
        </m.div>
      ))}
    </m.div>
  );
}

TopicsGrid.displayName = "TopicsGrid";
