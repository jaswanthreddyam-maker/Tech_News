"use client";

import React from "react";
import { ShimmerBase } from "./ShimmerBase";

/**
 * HeroSkeleton — 1:1 Skeleton for Hero Section Loading
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

      {/* Right 3D Ring Skeleton */}
      <div className="hidden lg:flex items-center justify-center w-[480px] h-[480px] relative">
        <ShimmerBase className="w-[300px] h-[380px] rounded-2xl shadow-2xl" />
      </div>
    </div>
  );
});
