"use client";

import React from "react";
import { ShimmerBase } from "./ShimmerBase";

interface AdaptiveCardSkeletonProps {
  className?: string;
}

/**
 * AdaptiveCardSkeleton — 1:1 Mirror for AdaptiveStoryCard
 */
export const AdaptiveCardSkeleton = React.memo(function AdaptiveCardSkeleton({
  className = "",
}: AdaptiveCardSkeletonProps) {
  return (
    <div
      className={`flex flex-col justify-between h-full p-4 rounded-xl bg-card/40 border border-border/40 space-y-4 shadow-sm ${className}`}
    >
      <div className="space-y-3">
        {/* Card Header (Category Badge) */}
        <div className="flex items-center justify-between">
          <ShimmerBase className="h-5 w-20 rounded-full" />
          <ShimmerBase className="h-3 w-12 rounded" />
        </div>

        {/* Media Asset (16:9 Aspect Ratio) */}
        <ShimmerBase className="w-full aspect-[16/9] rounded-lg" />

        {/* Title (2 lines) */}
        <div className="space-y-2 pt-1">
          <ShimmerBase className="h-5 w-[92%] rounded-md" />
          <ShimmerBase className="h-5 w-[68%] rounded-md" />
        </div>

        {/* Summary (2 lines) */}
        <div className="space-y-1.5 pt-1">
          <ShimmerBase className="h-3.5 w-full rounded" />
          <ShimmerBase className="h-3.5 w-[85%] rounded" />
        </div>
      </div>

      {/* Footer (Source + Read Time) */}
      <div className="pt-3 border-t border-border/30 flex items-center justify-between mt-auto">
        <ShimmerBase className="h-3 w-20 rounded" />
        <ShimmerBase className="h-3 w-16 rounded" />
      </div>
    </div>
  );
});
