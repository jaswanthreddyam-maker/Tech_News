"use client";

import React from "react";
import { ShimmerBase } from "./ShimmerBase";

interface EditorialCardSkeletonProps {
  isPrimary?: boolean;
}

/**
 * EditorialCardSkeleton — 1:1 Mirrored Skeleton for FloatingEditorialPanel
 * 
 * Guarantees zero CLS (Cumulative Layout Shift) and provides an editorial-quality
 * loading experience during fast scrolling or image decoding.
 */
export const EditorialCardSkeleton = React.memo(function EditorialCardSkeleton({ isPrimary = false }: EditorialCardSkeletonProps) {
  return (
    <div
      className={`
        relative flex flex-col w-full rounded-2xl overflow-hidden
        bg-[#121316]/90 backdrop-blur-xl border border-white/10
        ${isPrimary ? "md:col-span-2 min-h-[460px] sm:min-h-[500px]" : "min-h-[420px]"}
      `}
    >
      {/* 1. Media Showcase Placeholder (Exact Aspect / Height Match) */}
      <div className={`relative w-full overflow-hidden ${isPrimary ? "h-[240px] sm:h-[280px]" : "h-[210px] sm:h-[230px]"}`}>
        <ShimmerBase className="w-full h-full rounded-t-2xl rounded-b-none" />
      </div>

      {/* 2. Content Body Placeholder */}
      <div className="p-6 sm:p-8 flex flex-col flex-1 justify-between">
        <div>
          {/* Source & Category Metadata Rail Placeholder */}
          <div className="flex items-center gap-3 mb-4">
            <ShimmerBase className="h-3 w-20 rounded-full" />
            <span className="text-white/10">•</span>
            <ShimmerBase className="h-3 w-28 rounded-full" />
          </div>

          {/* Title Hierarchy Placeholder (3 lines with decreasing width) */}
          <div className="space-y-2.5 mb-4">
            <ShimmerBase className="h-6 sm:h-7 w-[95%] rounded-md" />
            <ShimmerBase className="h-6 sm:h-7 w-[78%] rounded-md" />
            {isPrimary && <ShimmerBase className="h-6 sm:h-7 w-[45%] rounded-md" />}
          </div>

          {/* Summary Placeholder (2 lines) */}
          <div className="space-y-2 mb-6">
            <ShimmerBase className="h-3.5 w-[92%] rounded" />
            <ShimmerBase className="h-3.5 w-[65%] rounded" />
          </div>
        </div>

        {/* 3. Footer Metadata & CTA Row Placeholder */}
        <div className="pt-4 border-t border-white/5 flex items-center justify-between mt-auto">
          <div className="flex items-center gap-3">
            <ShimmerBase className="h-3 w-24 rounded-full" />
            <span className="text-white/10">•</span>
            <ShimmerBase className="h-3 w-16 rounded-full" />
          </div>

          <ShimmerBase className="h-4 w-24 rounded-full" />
        </div>
      </div>
    </div>
  );
});
