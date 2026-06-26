"use client";

import React from "react";
import { Skeleton } from "@/design-system/components/Skeleton";
import { useLoadingState } from "@/design-system/hooks/useLoadingState";
import { cn } from "@/lib/utils";

export function HeroCarouselSkeleton() {
  const level = useLoadingState(true);

  return (
    <div 
      className={cn(
        "w-full border border-border bg-card/20 rounded-xl p-6 lg:p-8 transition-opacity duration-300",
        level === "hidden" ? "opacity-0" : "opacity-100"
      )}
    >
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Column Skeleton (Headline / Content) */}
        <div className="lg:col-span-4 flex flex-col justify-center h-full space-y-4">
          {/* Metadata Row */}
          <div className="flex gap-2 items-center">
            <Skeleton level={level} className="h-5 w-20 rounded-full" />
            <Skeleton level={level} className="h-3 w-16" />
            <Skeleton level={level} className="h-3 w-24" />
          </div>
          {/* Headline */}
          <Skeleton level={level} className="h-10 w-full" />
          <Skeleton level={level} className="h-10 w-5/6" />
          {/* Summary */}
          <div className="space-y-2 mt-4">
            <Skeleton level={level} className="h-4 w-full" />
            <Skeleton level={level} className="h-4 w-full" />
            <Skeleton level={level} className="h-4 w-2/3" />
          </div>
          {/* CTA */}
          <Skeleton level={level} className="h-5 w-32 mt-4" />
        </div>

        {/* Center Column Skeleton (Hero Image) */}
        <div className="lg:col-span-5 relative w-full h-[300px] md:h-[350px] lg:h-[450px]">
          <Skeleton level={level} className="absolute inset-0 w-full h-full rounded-none" />
        </div>

        {/* Right Column Skeleton (AI Insights Sidebar) */}
        <div className="lg:col-span-3 border border-border/80 rounded-xl p-5 space-y-4 flex flex-col">
          {/* Header */}
          <div className="flex gap-2 items-center pb-3 border-b border-border/60">
            <Skeleton level={level} className="h-5 w-5 rounded-full" />
            <Skeleton level={level} className="h-5 w-36" />
          </div>
          {/* Tabs header */}
          <div className="grid grid-cols-3 gap-1 bg-muted p-1 rounded-lg h-8">
            <Skeleton level={level} className="h-6 rounded" />
            <Skeleton level={level} className="h-6 rounded" />
            <Skeleton level={level} className="h-6 rounded" />
          </div>
          {/* List items */}
          <div className="space-y-4 flex-1 overflow-hidden mt-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="pb-3 border-b border-border/40 last:border-0 last:pb-0 space-y-2">
                <Skeleton level={level} className="h-3 w-16" />
                <Skeleton level={level} className="h-4 w-full" />
                <Skeleton level={level} className="h-3 w-5/6" />
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
