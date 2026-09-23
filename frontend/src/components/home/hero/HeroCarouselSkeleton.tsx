"use client";

import React from "react";
import { ShimmerBase } from "@/components/skeletons/ShimmerBase";

/**
 * HeroCarouselSkeleton — 1:1 Mirror for HeroScene (Pitch OLED Black Editorial Stage)
 */
export function HeroCarouselSkeleton() {
  return (
    <div className="relative w-full min-h-[580px] md:min-h-[640px] xl:min-h-[680px] pt-1 px-4 sm:px-6 lg:px-8 pb-4 flex items-center justify-center">
      <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-8 xl:gap-12 items-center w-full max-w-[1400px] mx-auto">
        
        {/* Left Editorial Panel Skeleton (lg:col-span-5) */}
        <div className="lg:col-span-5 flex flex-col justify-start max-w-[540px] w-full mx-auto lg:mx-0 z-20 order-1 lg:order-1 lg:-translate-y-[40px] pt-4 lg:pt-0 space-y-6">
          {/* Badge & Timestamp Row */}
          <div className="flex items-center gap-3">
            <ShimmerBase className="h-6 w-32 rounded-full" />
            <ShimmerBase className="h-4 w-20 rounded" />
          </div>

          {/* Headline (2-3 lines of large bold typography) */}
          <div className="space-y-3">
            <ShimmerBase className="h-10 sm:h-12 w-full rounded-lg" />
            <ShimmerBase className="h-10 sm:h-12 w-[88%] rounded-lg" />
            <ShimmerBase className="h-10 sm:h-12 w-[60%] rounded-lg" />
          </div>

          {/* Summary Excerpt */}
          <div className="space-y-2 pt-2">
            <ShimmerBase className="h-4 w-full rounded" />
            <ShimmerBase className="h-4 w-full rounded" />
            <ShimmerBase className="h-4 w-[75%] rounded" />
          </div>

          {/* Read Story CTA Button & Slide Controls */}
          <div className="pt-4 flex items-center gap-6">
            <ShimmerBase className="h-11 w-40 rounded-full" />
            <div className="flex items-center gap-2">
              {[...Array(5)].map((_, i) => (
                <ShimmerBase key={i} className="h-2 w-2 rounded-full" />
              ))}
            </div>
          </div>
        </div>

        {/* Right 3D Ring Stage Skeleton (lg:col-span-7) */}
        <div className="lg:col-span-7 relative w-full flex items-center justify-center z-10 order-2 lg:order-2 h-[420px] sm:h-[460px] lg:h-[480px] -mt-12 sm:-mt-12 lg:mt-0 lg:-translate-y-[30px]">
          {/* Left Flanking Perspective Card Skeleton */}
          <div className="hidden sm:block absolute left-4 lg:left-12 w-[220px] md:w-[240px] aspect-[4/5] rounded-2xl bg-card/20 border border-white/5 opacity-40 transform -rotate-12 scale-90" />

          {/* Active Center 3D Extruded Slab Card Skeleton */}
          <div className="relative z-20 w-[247px] sm:w-[285px] md:w-[304px] aspect-[4/5] rounded-2xl bg-black/90 border border-white/20 p-4 flex flex-col justify-between shadow-[0_25px_50px_-10px_rgba(0,0,0,0.95)]">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <ShimmerBase className="h-5 w-20 rounded-full" />
                <ShimmerBase className="h-4 w-12 rounded" />
              </div>
              <ShimmerBase className="w-full aspect-[16/10] rounded-xl" />
              <div className="space-y-2 pt-1">
                <ShimmerBase className="h-5 w-full rounded-md" />
                <ShimmerBase className="h-5 w-4/5 rounded-md" />
              </div>
            </div>
            <div className="pt-3 border-t border-white/10 flex items-center justify-between">
              <ShimmerBase className="h-3 w-20 rounded" />
              <ShimmerBase className="h-3 w-16 rounded" />
            </div>
          </div>

          {/* Right Flanking Perspective Card Skeleton */}
          <div className="hidden sm:block absolute right-4 lg:right-12 w-[220px] md:w-[240px] aspect-[4/5] rounded-2xl bg-card/20 border border-white/5 opacity-40 transform rotate-12 scale-90" />
        </div>

      </div>
    </div>
  );
}
