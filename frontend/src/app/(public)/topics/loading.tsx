import React from "react";
import { Container } from "@/components/layout/Container";
import { ChevronRight, Search, Grid, List, SlidersHorizontal } from "lucide-react";

export default function TopicsLoading() {
  return (
    <Container className="py-10 space-y-12 min-h-screen transition-colors duration-300 bg-background text-foreground">
      {/* ── Breadcrumb and Header with Orbit Graphic Skeleton ── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8 pb-10 border-b border-border/40">
        <div className="space-y-4 max-w-2xl flex-1">
          {/* Breadcrumbs */}
          <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground/60">
            <span>Home</span>
            <ChevronRight className="w-3.5 h-3.5" />
            <span className="font-semibold text-foreground">Topics</span>
          </div>

          {/* Badge */}
          <div className="h-5 w-36 bg-muted rounded-full animate-pulse"></div>
          
          {/* Title */}
          <div className="h-10 w-64 md:w-80 bg-muted rounded-lg animate-pulse"></div>
          
          {/* Description */}
          <div className="space-y-2">
            <div className="h-4 w-full bg-muted rounded animate-pulse"></div>
            <div className="h-4 w-5/6 bg-muted rounded animate-pulse"></div>
          </div>
        </div>

        {/* Orbit Graphic Placeholder */}
        <div className="shrink-0 w-80 h-44 rounded-2xl border border-border/30 bg-card/45 animate-pulse flex items-center justify-center">
          <div className="w-10 h-10 rounded-full bg-muted"></div>
        </div>
      </div>

      {/* ── Telemetry Metrics Cards Skeleton (4 cards) ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        {[1, 2, 3, 4].map((i) => (
          <div 
            key={i} 
            className="rounded-xl border border-border bg-card/45 p-4 md:p-5 flex items-center gap-4 animate-pulse shadow-sm"
          >
            <div className="w-11 h-11 rounded-lg bg-muted shrink-0"></div>
            <div className="space-y-2 flex-1">
              <div className="h-5 w-12 bg-muted rounded"></div>
              <div className="h-3 w-16 bg-muted rounded"></div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Search, Sort, Filters Control Strip Skeleton ── */}
      <div className="flex flex-col md:flex-row gap-4 items-stretch md:items-center justify-between">
        {/* Search Input skeleton */}
        <div className="relative max-w-md w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/35" />
          <div className="w-full h-10 rounded-lg bg-card border border-border pl-9 animate-pulse"></div>
        </div>

        {/* Controls skeleton */}
        <div className="flex flex-wrap items-center gap-3 justify-end">
          <div className="w-28 h-10 bg-card border border-border rounded-lg animate-pulse"></div>
          <div className="w-20 h-10 bg-card border border-border rounded-lg animate-pulse"></div>
          <div className="w-24 h-10 bg-card border border-border rounded-lg animate-pulse"></div>
        </div>
      </div>

      {/* ── Category Filter Pills Skeleton ── */}
      <div className="flex items-center gap-2 overflow-x-auto pb-3">
        {[1, 2, 3, 4, 5, 6, 7].map((i) => (
          <div 
            key={i} 
            className="px-6 py-3.5 rounded-full bg-card border border-border animate-pulse shrink-0 w-24 h-7"
          ></div>
        ))}
      </div>

      {/* ── Topics Grid Skeleton ── */}
      <div className="space-y-6">
        <div className="border-b border-border/40 pb-3 flex items-center justify-between">
          <div className="h-6 w-40 bg-muted rounded animate-pulse"></div>
          <div className="h-4 w-28 bg-muted rounded animate-pulse"></div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="rounded-xl border border-border bg-card/65 p-5 flex flex-col justify-between shadow-sm animate-pulse h-[260px]"
            >
              <div className="space-y-4">
                {/* Header */}
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-11 h-11 rounded-xl bg-muted shrink-0"></div>
                    <div className="space-y-2">
                      <div className="h-5 w-32 bg-muted rounded"></div>
                      <div className="h-3.5 w-20 bg-muted rounded"></div>
                    </div>
                  </div>
                  <div className="w-4 h-4 bg-muted rounded shrink-0"></div>
                </div>

                {/* Description */}
                <div className="space-y-2">
                  <div className="h-3.5 w-full bg-muted rounded"></div>
                  <div className="h-3.5 w-full bg-muted rounded"></div>
                  <div className="h-3.5 w-4/5 bg-muted rounded"></div>
                </div>
              </div>

              {/* Progress & Button */}
              <div className="space-y-3 pt-4 border-t border-border/40">
                <div className="space-y-1.5">
                  <div className="h-2.5 w-12 bg-muted rounded"></div>
                  <div className="h-1.5 w-full bg-muted rounded-full"></div>
                </div>
                <div className="h-8 w-full bg-muted rounded-lg"></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Trending Section Skeleton */}
      <div className="border border-border/60 p-6 rounded-xl space-y-4 animate-pulse">
        <div className="h-5 w-32 bg-muted rounded"></div>
        <div className="flex flex-wrap gap-2">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-7 w-20 bg-muted rounded-full"></div>
          ))}
        </div>
      </div>

      {/* Latest Global Articles Section Skeleton */}
      <div className="space-y-6">
        <div className="border-b border-border/40 pb-3">
          <div className="h-6 w-44 bg-muted rounded animate-pulse"></div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="border border-border bg-card/45 p-5 rounded-xl flex flex-col justify-between shadow-sm animate-pulse h-48"
            >
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className="w-12 h-4 bg-muted rounded"></div>
                  <div className="w-16 h-3 bg-muted rounded"></div>
                </div>
                <div className="h-5 w-5/6 bg-muted rounded"></div>
                <div className="space-y-1.5">
                  <div className="h-3.5 w-full bg-muted rounded"></div>
                  <div className="h-3.5 w-4/5 bg-muted rounded"></div>
                </div>
              </div>
              <div className="pt-4 border-t border-border/40 flex items-center justify-between">
                <div className="w-24 h-3.5 bg-muted rounded"></div>
                <div className="w-16 h-3.5 bg-muted rounded"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Container>
  );
}
