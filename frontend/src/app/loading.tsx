import React from "react";
import { Container } from "@/components/layout/Container";
import { ShimmerBase } from "@/components/skeletons/ShimmerBase";
import { HeroCarouselSkeleton } from "@/components/home/hero/HeroCarouselSkeleton";
import { TrendingSkeleton } from "@/components/skeletons/TrendingSkeleton";

export default function Loading() {
  return (
    <div className="flex flex-col min-h-screen bg-black text-foreground">
      {/* Zero-G Floating Nav Capsule Skeleton */}
      <div className="fixed top-4 inset-x-0 z-50 flex justify-center pointer-events-none px-4">
        <div className="w-full max-w-[680px] h-12 rounded-full border border-white/[0.08] bg-black/60 backdrop-blur-xl px-5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShimmerBase className="w-6 h-6 rounded-full" />
            <ShimmerBase className="h-4 w-28 rounded" />
          </div>
          <div className="flex items-center gap-3">
            <ShimmerBase className="h-7 w-32 rounded-full hidden sm:block" />
            <ShimmerBase className="w-8 h-8 rounded-full" />
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 w-full pt-16 sm:pt-20">
        <Container size="wide" className="mt-2">
          <HeroCarouselSkeleton />
        </Container>

        <Container size="wide" className="mt-12 mb-20">
          <TrendingSkeleton />
        </Container>
      </main>
    </div>
  );
}
