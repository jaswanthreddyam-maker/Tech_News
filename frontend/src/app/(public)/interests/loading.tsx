import React from "react";
import { ShimmerBase } from "@/components/skeletons/ShimmerBase";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export function InterestsGridSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <div
          key={i}
          className="flex flex-col gap-3 p-5 rounded-xl border border-border/40 bg-background/50"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShimmerBase className="h-5 w-14 rounded" />
              <ShimmerBase className="h-5 w-28 rounded" />
            </div>
            <ShimmerBase className="h-4 w-16 rounded" />
          </div>
          
          <div className="space-y-2 mt-1">
            <div className="flex justify-between">
              <ShimmerBase className="h-3 w-20 rounded" />
              <ShimmerBase className="h-3 w-8 rounded" />
            </div>
            <ShimmerBase className="h-1.5 w-full rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function InterestsSkeleton() {
  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl space-y-8">
      {/* Header and Trust Indicators */}
      <section className="space-y-4">
        <div className="flex items-center gap-3">
          <ShimmerBase className="w-10 h-10 rounded-full shrink-0" />
          <ShimmerBase className="h-10 w-64 rounded-xl" />
        </div>
        
        <Card className="bg-muted/30 border-muted/50">
          <CardContent className="p-6 flex items-start gap-4">
            <ShimmerBase className="w-12 h-12 rounded-full shrink-0" />
            <div className="space-y-2 flex-1">
              <ShimmerBase className="h-5 w-52 rounded" />
              <ShimmerBase className="h-4 w-full rounded" />
              <ShimmerBase className="h-4 w-3/4 rounded" />
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Derived Interests */}
      <section>
        <Card className="bg-card/50 border-border/50 backdrop-blur shadow-xl">
          <CardHeader className="border-b border-border/50 pb-6">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <ShimmerBase className="w-6 h-6 rounded" />
                  <ShimmerBase className="h-7 w-48 rounded" />
                </div>
                <ShimmerBase className="h-4 w-80 rounded" />
              </div>
              <ShimmerBase className="h-7 w-32 rounded-full" />
            </div>
          </CardHeader>
          <CardContent className="pt-6">
            <InterestsGridSkeleton />
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

export default function InterestsLoading() {
  return <InterestsSkeleton />;
}
