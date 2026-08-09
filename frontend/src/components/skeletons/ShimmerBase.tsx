"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface ShimmerBaseProps {
  className?: string;
  style?: React.CSSProperties;
}

/**
 * ShimmerBase — Reusable GPU-Accelerated Skeleton Block
 * 
 * Uses pure CSS shimmer animation (2.2s duration) with subtle 2-7% opacity.
 * Zero JavaScript rerender overhead.
 */
export const ShimmerBase = React.memo(function ShimmerBase({ className, style }: ShimmerBaseProps) {
  return (
    <div
      className={cn("skeleton-shimmer-bg rounded-lg", className)}
      style={style}
    />
  );
});
