"use client";

import React from "react";
import { ShimmerBase } from "./ShimmerBase";

/**
 * HeroSkeleton — 1:1 Perspective Silhouette for Hero 3D Ring Section Loading
 */
export const HeroSkeleton = React.memo(function HeroSkeleton() {
  return (
    <div className="w-full min-h-[580px] lg:min-h-[640px] flex items-center justify-between px-4 sm:px-8 max-w-[1400px] mx-auto py-12">
      {/* Left Editorial Panel Skeleton */}
      <div className="w-full max-w-[540px] space-y-6">
        <div className="flex items-center gap-3">
          <ShimmerBase className="h-6 w-36 rounded-md" />
          <ShimmerBase className="h-4 w-16 rounded-md" />
        </div>

        <div className="space-y-3">
          <ShimmerBase className="h-10 sm:h-12 w-full rounded-lg" />
          <ShimmerBase className="h-10 sm:h-12 w-[85%] rounded-lg" />
        </div>

        <ShimmerBase className="h-6 w-32 rounded-full pt-2" />
      </div>

      {/* Right 3D Ring Perspective Skeleton */}
      <div className="hidden lg:flex items-center justify-center w-[520px] h-[480px] relative">
        {/* Left receding wing card */}
        <div className="absolute -left-8 w-[240px] h-[340px] rounded-2xl bg-neutral-900/30 border border-white/5 opacity-40 -rotate-6 scale-90" />
        
        {/* Center active card */}
        <div className="relative z-10 w-[280px] h-[380px] rounded-2xl bg-neutral-900/60 border border-white/10 shadow-2xl p-4 flex flex-col justify-end overflow-hidden">
          <ShimmerBase className="w-full h-full absolute inset-0 opacity-40" />
          <div className="relative z-20 space-y-2">
            <ShimmerBase className="h-4 w-20 rounded" />
            <ShimmerBase className="h-6 w-full rounded" />
            <ShimmerBase className="h-4 w-3/4 rounded" />
          </div>
        </div>

        {/* Right receding wing card */}
        <div className="absolute -right-8 w-[240px] h-[340px] rounded-2xl bg-neutral-900/30 border border-white/5 opacity-40 rotate-6 scale-90" />
      </div>
    </div>
  );
});

