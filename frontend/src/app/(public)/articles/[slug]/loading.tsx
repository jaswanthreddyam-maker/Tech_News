"use client";

import React from "react";
import { Skeleton } from "@/design-system/components/Skeleton";
import { useLoadingState } from "@/design-system/hooks/useLoadingState";
import { Container } from "@/components/layout/Container";

export default function ArticleLoading() {
  const level = useLoadingState(true);

  return (
    <Container size="wide" className="mt-8 mb-20">
      <div className="flex flex-col xl:flex-row gap-8 lg:gap-12 relative xl:ml-12">
        {/* Actions Placeholder */}
        <div className="hidden xl:flex flex-col gap-4 absolute -left-16 top-0">
          {[1, 2, 3, 4].map(i => (
            <Skeleton key={i} level={level} className="w-10 h-10 rounded-full" />
          ))}
        </div>

        {/* Main Content Column */}
        <div className="flex-1 min-w-0 max-w-[72ch] mx-auto xl:mx-0 w-full">
          {/* Header */}
          <div className="mb-8">
            <Skeleton level={level} className="h-10 w-full mb-3" />
            <Skeleton level={level} className="h-10 w-4/5 mb-6" />
            <div className="flex items-center gap-4 mb-6">
              <Skeleton level={level} className="h-5 w-24 rounded-full" />
              <Skeleton level={level} className="h-5 w-24" />
              <Skeleton level={level} className="h-5 w-32" />
            </div>
            {/* Reading Preferences Control Bar */}
            <div className="flex items-center justify-between border-t border-b border-border/50 py-3">
              <div className="flex gap-2">
                <Skeleton level={level} className="h-6 w-16 rounded-full" />
                <Skeleton level={level} className="h-6 w-20 rounded-full" />
                <Skeleton level={level} className="h-6 w-20 rounded-full" />
              </div>
              <div className="flex gap-2">
                <Skeleton level={level} className="h-6 w-8 rounded-md" />
                <Skeleton level={level} className="h-6 w-8 rounded-md" />
              </div>
            </div>
          </div>

          {/* Hero Image */}
          <div className="mb-10">
            <Skeleton level={level} className="w-full h-[350px] md:h-[450px] rounded-xl" />
          </div>

          {/* AI Summary Placeholder */}
          <div className="mb-10 border border-border p-6 rounded-xl">
            <Skeleton level={level} className="h-5 w-32 mb-4" />
            <Skeleton level={level} className="h-4 w-full mb-2" />
            <Skeleton level={level} className="h-4 w-full mb-2" />
            <Skeleton level={level} className="h-4 w-4/5" />
          </div>

          {/* Article Content */}
          <article className="mb-16 space-y-4">
            <Skeleton level={level} className="h-5 w-full" />
            <Skeleton level={level} className="h-5 w-full" />
            <Skeleton level={level} className="h-5 w-11/12" />
            <Skeleton level={level} className="h-5 w-full mt-8" />
            <Skeleton level={level} className="h-5 w-4/5" />
          </article>
        </div>

        {/* Right Sidebar */}
        <aside className="hidden xl:block w-[350px] shrink-0 space-y-8">
          <div className="sticky top-24 space-y-8">
            {/* Source Credibility */}
            <div className="border border-border p-5 rounded-xl">
              <Skeleton level={level} className="h-5 w-40 mb-4" />
              <Skeleton level={level} className="h-10 w-full mb-2" />
              <Skeleton level={level} className="h-4 w-3/4" />
            </div>
            
            {/* TOC */}
            <div className="border border-border p-5 rounded-xl">
              <Skeleton level={level} className="h-5 w-32 mb-4" />
              <div className="space-y-3">
                {[1, 2, 3, 4].map(i => (
                  <Skeleton key={i} level={level} className="h-4 w-full" />
                ))}
              </div>
            </div>
            
            {/* Related */}
            <div className="border border-border p-5 rounded-xl">
              <Skeleton level={level} className="h-5 w-32 mb-4" />
              <div className="space-y-4">
                {[1, 2, 3].map(i => (
                  <div key={i}>
                    <Skeleton level={level} className="h-4 w-full mb-2" />
                    <Skeleton level={level} className="h-4 w-3/4 mb-2" />
                    <Skeleton level={level} className="h-3 w-1/2" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </aside>
      </div>
    </Container>
  );
}
