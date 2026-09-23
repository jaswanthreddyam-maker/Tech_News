import React from "react";
import { Container } from "@/components/layout/Container";
import { ShimmerBase } from "@/components/skeletons/ShimmerBase";
import { AdaptiveCardSkeleton } from "@/components/skeletons/AdaptiveCardSkeleton";

export function FeedSkeleton() {
  return (
    <div className="space-y-8">
      {/* Editorial Filter Chips Skeleton */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
        {["All Stories", "Breaking News", "Newsletters", "Roundups", "Opinions", "Reviews"].map((label, i) => (
          <ShimmerBase key={i} className="h-9 w-28 rounded-full shrink-0" />
        ))}
      </div>

      {/* Adaptive Cards Grid (3 columns matching production layout) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {[...Array(6)].map((_, i) => (
          <AdaptiveCardSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}

export default function FeedLoading() {
  return (
    <Container className="py-12">
      {/* Header Skeleton */}
      <div className="mb-12 space-y-3">
        <ShimmerBase className="h-10 w-44 rounded-xl" />
        <ShimmerBase className="h-5 w-80 max-w-full rounded-md" />
      </div>

      <FeedSkeleton />
    </Container>
  );
}
