"use client";

import React from "react";
import { ShimmerBase } from "./ShimmerBase";

/**
 * TrendingSkeleton — 1:1 Skeleton for Trending Stories Section
 */
export const TrendingSkeleton = React.memo(function TrendingSkeleton() {
  return (
    <div className="w-full max-w-[1400px] mx-auto py-8">
      {/* Header Placeholder */}
      <div className="flex items-center gap-3 mb-9">
        <ShimmerBase className="w-8 h-8 rounded-xl" />
        <div className="space-y-2">
          <ShimmerBase className="h-7 w-48 rounded-md" />
          <ShimmerBase className="h-3 w-72 rounded" />
        </div>
      </div>

      {/* Grid Layout (5 cols Featured + 7 cols Compact Tiles) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 w-full items-stretch">
        {/* Featured Story Skeleton */}
        <div className="lg:col-span-5 flex flex-col min-h-[460px] p-6 rounded-[18px] bg-neutral-950/75 border border-white/10">
          <ShimmerBase className="w-full aspect-[4/3] rounded-[12px] mb-5" />
          <ShimmerBase className="h-4 w-20 rounded-md mb-3" />
          <ShimmerBase className="h-7 w-[90%] rounded-md mb-2" />
          <ShimmerBase className="h-7 w-[65%] rounded-md mb-4" />
          <ShimmerBase className="h-3.5 w-full rounded mb-2" />
          <ShimmerBase className="h-3.5 w-[80%] rounded mb-5" />
          <div className="mt-auto pt-4 border-t border-white/5 flex justify-between">
            <ShimmerBase className="h-3 w-28 rounded-full" />
            <ShimmerBase className="h-3 w-16 rounded-full" />
          </div>
        </div>

        {/* Compact Story Tiles Grid (6 tiles) */}
        <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="flex flex-row items-stretch justify-between gap-4 p-5 h-full rounded-[16px] bg-neutral-950/65 border border-white/10">
              <div className="flex flex-col flex-1 min-w-0 justify-between">
                <div>
                  <ShimmerBase className="h-3 w-16 rounded mb-2" />
                  <ShimmerBase className="h-5 w-[90%] rounded mb-2" />
                  <ShimmerBase className="h-5 w-[70%] rounded mb-3" />
                </div>
                <ShimmerBase className="h-3 w-24 rounded-full mt-auto" />
              </div>
              <ShimmerBase className="w-[80px] h-[80px] rounded-[10px] flex-none" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
});
