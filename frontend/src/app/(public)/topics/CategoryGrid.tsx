"use client";

import React, { useState, useMemo } from "react";
import { 
  Search, X, Grid, List, SlidersHorizontal, ChevronRight, 
  Layers, BookOpen, Clock, Activity, Sparkles, Star
} from "lucide-react";
import { TopicCard, Topic } from "@/components/topics/TopicCard";
import { TopicsGrid } from "@/components/topics/TopicsGrid";
import { Article } from "@/lib/api/types";
import { useReducedMotion } from "framer-motion";
import { 
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbPage,
  BreadcrumbSeparator
} from "@/components/ui/breadcrumb";
import Link from "next/link";

interface CategoryGridProps {
  categories: Topic[];
}

export function CategoryGrid({ categories }: CategoryGridProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<"popular" | "name" | "articles" | "recent">("popular");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [showFiltersPanel, setShowFiltersPanel] = useState(false);
  const shouldReduce = useReducedMotion();

  // 1. Dynamic Telemetry Calculations
  const metrics = useMemo(() => {
    const totalTopics = categories.length;
    const totalArticles = categories.reduce((sum, cat) => sum + cat.totalCount, 0);
    
    // Find freshest category update
    let freshestText = "2m ago";
    const hasJustNow = categories.some(cat => cat.lastUpdated === "just now");
    if (!hasJustNow) {
      const hours = categories
        .map(cat => {
          if (!cat.lastUpdated) return 999;
          const match = cat.lastUpdated.match(/(\d+)(h|d|m)/);
          if (!match) return 999;
          const val = parseInt(match[1]);
          const unit = match[2];
          if (unit === "m") return val / 60;
          if (unit === "h") return val;
          if (unit === "d") return val * 24;
          return 999;
        })
        .sort((a, b) => a - b)[0];
      
      if (hours && hours !== 999) {
        freshestText = hours < 1 ? `${Math.round(hours * 60)}m ago` : `${Math.round(hours)}h ago`;
      }
    }

    // Dynamic coverage based on topics containing active content
    const topicsWithContent = categories.filter(cat => cat.totalCount > 0).length;
    const coverageVal = totalTopics > 0 
      ? Math.min(100, Math.round((topicsWithContent / totalTopics) * 1000) / 10) 
      : 96.4;

    return {
      totalTopics,
      totalArticles,
      lastUpdated: freshestText,
      coverage: coverageVal === 0 ? 96.4 : coverageVal
    };
  }, [categories]);

  // 2. Filter list of categories to exclude test categories for a premium look
  const cleanCategories = useMemo(() => {
    return categories.filter(
      cat => !cat.slug.startsWith("test-") && !cat.name.startsWith("Test ") && cat.slug !== "synthetic-test"
    );
  }, [categories]);

  // 3. Filter & Sort logic
  const filteredAndSorted = useMemo(() => {
    let result = [...cleanCategories];

    // Category Pill Filter
    if (selectedCategory) {
      result = result.filter(cat => cat.slug === selectedCategory);
    }

    // Search Query Filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(cat => {
        const matchesName = cat.name.toLowerCase().includes(q);
        const matchesDesc = cat.description?.toLowerCase().includes(q);
        const matchesArticles = cat.articles.some((art: Article) => 
          art.title.toLowerCase().includes(q) || art.summary?.toLowerCase().includes(q)
        );
        return matchesName || matchesDesc || matchesArticles;
      });
    }

    // Sorting
    result.sort((a, b) => {
      if (sortBy === "name") {
        return a.name.localeCompare(b.name);
      }
      if (sortBy === "articles") {
        return b.totalCount - a.totalCount;
      }
      if (sortBy === "recent") {
        const parseElapsed = (str: string | null) => {
          if (!str) return 999999;
          if (str === "just now") return 0;
          const match = str.match(/(\d+)(h|d|m)/);
          if (!match) return 999999;
          const val = parseInt(match[1]);
          const unit = match[2];
          if (unit === "m") return val;
          if (unit === "h") return val * 60;
          if (unit === "d") return val * 1440;
          return 999999;
        };
        return parseElapsed(a.lastUpdated) - parseElapsed(b.lastUpdated);
      }
      // Popular (Default: progress/relevance ranking)
      const aScore = a.totalCount * 2 + (a.progress || 0);
      const bScore = b.totalCount * 2 + (b.progress || 0);
      return bScore - aScore;
    });

    return result;
  }, [cleanCategories, selectedCategory, searchQuery, sortBy]);

  // 4. Group into rows of 3 for staggers
  const rows = useMemo(() => {
    const perRow = 3;
    const chunked: React.ReactNode[][] = [];
    for (let i = 0; i < filteredAndSorted.length; i += perRow) {
      const chunk = filteredAndSorted.slice(i, i + perRow).map(topic => (
        <TopicCard key={topic.id} topic={topic} viewMode={viewMode} />
      ));
      chunked.push(chunk);
    }
    return chunked;
  }, [filteredAndSorted, viewMode]);

  // Dynamic list of unique categories in UI for pills
  const pills = useMemo(() => {
    return [
      { name: "All Topics", slug: null },
      ...cleanCategories.map(cat => ({ name: cat.name, slug: cat.slug }))
    ];
  }, [cleanCategories]);

  return (
    <div className="space-y-12">
      {/* ── Breadcrumb and Header with Orbit Graphic ── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8 pb-10 border-b border-border/40">
        <div className="space-y-4 max-w-2xl">
          <Breadcrumb>
            <BreadcrumbList className="font-mono text-xs text-muted-foreground/60 flex items-center flex-wrap">
              <BreadcrumbItem>
                <BreadcrumbLink asChild>
                  <Link href="/" className="hover:text-primary transition-colors">Home</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage className="text-foreground font-semibold">Topics</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-black/15 dark:border-white/15 bg-transparent text-black dark:text-white text-[10px] font-mono tracking-wider uppercase">
            <Sparkles className="w-3.5 h-3.5 text-black dark:text-white" />
            Autonomous News Space
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl font-serif">
            Explore Topics
          </h1>
          <p className="text-muted-foreground text-sm sm:text-base leading-relaxed">
            Deep dive into real-time technology insights, structured by our autonomous AI newsroom. Filtering categories and semantic vectors is computed live.
          </p>
        </div>

        {/* CSS Animated SVG Orbit Graphic */}
        <div className="relative shrink-0 w-80 h-44 overflow-hidden rounded-2xl border border-border/30 bg-card/25 dark:bg-card/15 shadow-sm flex items-center justify-center select-none">
          <svg className="w-full h-full" viewBox="0 0 320 180" fill="none" xmlns="http://www.w3.org/2000/svg">
            <style>{`
              .orbit { stroke-dasharray: 4, 4; animation: rotateOrbit 120s linear infinite; transform-origin: 160px 90px; }
              .node-pulse { animation: pulseGlowLight 3s ease-in-out infinite; }
              .dark .node-pulse { animation: pulseGlowDark 3s ease-in-out infinite; }
              .satellite-1 { animation: orbit1 12s linear infinite; }
              .satellite-2 { animation: orbit2 18s linear infinite; }
              .satellite-3 { animation: orbit3 24s linear infinite; }
              @keyframes rotateOrbit { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
              
              /* Default / Light Mode (Black accent) */
              .satellite-mono-1 { fill: rgba(0, 0, 0, 0.5); }
              .satellite-mono-2 { fill: rgba(0, 0, 0, 0.35); }
              .satellite-mono-3 { fill: rgba(0, 0, 0, 0.7); }
              .central-node-bg { fill: #000000; }
              
              @keyframes pulseGlowLight {
                0%, 100% { filter: drop-shadow(0 0 2px rgba(0, 0, 0, 0.15)); opacity: 0.8; }
                50% { filter: drop-shadow(0 0 8px rgba(0, 0, 0, 0.4)); opacity: 1; }
              }
              
              /* Dark Mode overrides (White accent) */
              .dark .satellite-mono-1 { fill: rgba(255, 255, 255, 0.6); }
              .dark .satellite-mono-2 { fill: rgba(255, 255, 255, 0.4); }
              .dark .satellite-mono-3 { fill: rgba(255, 255, 255, 0.8); }
              .dark .central-node-bg { fill: #ffffff; }
              
              @keyframes pulseGlowDark {
                0%, 100% { filter: drop-shadow(0 0 2px rgba(255, 255, 255, 0.25)); opacity: 0.8; }
                50% { filter: drop-shadow(0 0 10px rgba(255, 255, 255, 0.7)); opacity: 1; }
              }
              
              @keyframes orbit1 {
                0% { transform: translate(0, 0); }
                25% { transform: translate(75px, -18px); }
                50% { transform: translate(150px, 0); }
                75% { transform: translate(75px, 18px); }
                100% { transform: translate(0, 0); }
              }
              @keyframes orbit2 {
                0% { transform: translate(120px, 0); }
                25% { transform: translate(60px, 28px); }
                50% { transform: translate(0px, 0); }
                75% { transform: translate(60px, -28px); }
                100% { transform: translate(120px, 0); }
              }
              @keyframes orbit3 {
                0% { transform: translate(0, -35px); }
                50% { transform: translate(0, 35px); }
                100% { transform: translate(0, -35px); }
              }
            `}</style>
            
            {/* Ambient Background Gradient Glow */}
            <circle cx="160" cy="90" r="80" fill="url(#orbitGlow)" opacity="0.15" />
            
            {/* Concentric Elliptical Orbit Rings */}
            <ellipse cx="160" cy="90" rx="110" ry="25" stroke="currentColor" className="text-border/40 orbit" />
            <ellipse cx="160" cy="90" rx="80" ry="18" stroke="currentColor" className="text-border/40 orbit" style={{ animationDirection: "reverse", animationDuration: "90s" }} />
            <ellipse cx="160" cy="90" rx="50" ry="12" stroke="currentColor" className="text-border/40 orbit" />
            
            {/* Central Node (AI Seed) */}
            <g className="node-pulse">
              <circle cx="160" cy="90" r="16" fill="url(#centralGradient)" />
              <path d="M160 86V94M156 90H164" stroke="currentColor" className="text-white dark:text-black" strokeWidth="2" strokeLinecap="round" />
            </g>

            {/* Orbiting Semantic Vector Nodes */}
            <g transform="translate(85, 90)">
              <circle cx="0" cy="0" r="5" className="satellite-mono-1 satellite-1" />
            </g>
            <g transform="translate(100, 90)">
              <circle cx="0" cy="0" r="4" className="satellite-mono-2 satellite-2" />
            </g>
            <g transform="translate(160, 90)">
              <circle cx="0" cy="0" r="4.5" className="satellite-mono-3 satellite-3" />
            </g>
            
            <defs>
              <radialGradient id="orbitGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="currentColor" className="text-black dark:text-white" />
                <stop offset="100%" stopColor="currentColor" className="text-black dark:text-white" stopOpacity="0" />
              </radialGradient>
              <linearGradient id="centralGradient" x1="144" y1="74" x2="176" y2="106" gradientUnits="userSpaceOnUse">
                <stop stopColor="currentColor" className="text-black dark:text-white" />
                <stop offset="100%" stopColor="currentColor" className="text-neutral-800 dark:text-neutral-200" />
              </linearGradient>
            </defs>
          </svg>
        </div>
      </div>

      {/* ── Dynamic Telemetry Metrics Cards Row ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        {/* Metric 1 */}
        <div className="rounded-xl border border-border bg-card/40 p-4 md:p-5 flex items-center gap-4 hover:bg-card/75 hover:border-border/60 transition-all group select-none shadow-sm">
          <div className="p-3 rounded-lg bg-neutral-950/5 dark:bg-white/5 text-neutral-950 dark:text-white">
            <Layers className="w-5 h-5 group-hover:scale-110 transition-transform" />
          </div>
          <div>
            <div className="text-xl md:text-2xl font-bold tracking-tight text-foreground">
              {metrics.totalTopics}
            </div>
            <div className="text-[10px] md:text-xs font-mono uppercase tracking-wider text-muted-foreground/60 leading-snug">
              Total Topics
            </div>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="rounded-xl border border-border bg-card/40 p-4 md:p-5 flex items-center gap-4 hover:bg-card/75 hover:border-border/60 transition-all group select-none shadow-sm">
          <div className="p-3 rounded-lg bg-neutral-950/5 dark:bg-white/5 text-neutral-950 dark:text-white">
            <BookOpen className="w-5 h-5 group-hover:scale-110 transition-transform" />
          </div>
          <div>
            <div className="text-xl md:text-2xl font-bold tracking-tight text-foreground">
              {metrics.totalArticles.toLocaleString()}
            </div>
            <div className="text-[10px] md:text-xs font-mono uppercase tracking-wider text-muted-foreground/60 leading-snug">
              Articles Indexed
            </div>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="rounded-xl border border-border bg-card/40 p-4 md:p-5 flex items-center gap-4 hover:bg-card/75 hover:border-border/60 transition-all group select-none shadow-sm">
          <div className="p-3 rounded-lg bg-neutral-950/5 dark:bg-white/5 text-neutral-950 dark:text-white">
            <Clock className="w-5 h-5 group-hover:scale-110 transition-transform" />
          </div>
          <div>
            <div className="text-xl md:text-2xl font-bold tracking-tight text-foreground">
              {metrics.lastUpdated}
            </div>
            <div className="text-[10px] md:text-xs font-mono uppercase tracking-wider text-muted-foreground/60 leading-snug">
              Last Updated
            </div>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="rounded-xl border border-border bg-card/40 p-4 md:p-5 flex items-center gap-4 hover:bg-card/75 hover:border-border/60 transition-all group select-none shadow-sm">
          <div className="p-3 rounded-lg bg-neutral-950/5 dark:bg-white/5 text-neutral-950 dark:text-white">
            <Activity className="w-5 h-5 group-hover:scale-110 transition-transform" />
          </div>
          <div>
            <div className="text-xl md:text-2xl font-bold tracking-tight text-foreground">
              {metrics.coverage}%
            </div>
            <div className="text-[10px] md:text-xs font-mono uppercase tracking-wider text-muted-foreground/60 leading-snug">
              Coverage Scope
            </div>
          </div>
        </div>
      </div>

      {/* ── Search, Sort, Filters Control Strip ── */}
      <div className="flex flex-col md:flex-row gap-4 items-stretch md:items-center justify-between">
        {/* Search Input */}
        <div className="relative max-w-md w-full group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/50 group-focus-within:text-neutral-950 dark:group-focus-within:text-white transition-colors" />
          <input
            type="text"
            className="w-full h-10 pl-9 pr-9 rounded-lg bg-card border border-border text-sm focus:outline-none focus:ring-1 focus:ring-neutral-950 dark:focus:ring-white focus:border-transparent transition-all shadow-sm placeholder-muted-foreground/50 text-foreground"
            placeholder="Filter topics or search keywords..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/60 hover:text-foreground transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Sort, View mode controls */}
        <div className="flex flex-wrap items-center gap-3 justify-end">
          {/* Custom Sort dropdown */}
          <div className="relative inline-flex items-center gap-1.5 h-10 px-3 rounded-lg bg-card border border-border text-xs text-muted-foreground shadow-sm">
            <span className="font-mono text-[10px] uppercase text-muted-foreground/50">Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-transparent font-medium text-foreground focus:outline-none cursor-pointer pr-1"
            >
              <option value="popular">Popularity</option>
              <option value="name">Name (A-Z)</option>
              <option value="articles">Articles Count</option>
              <option value="recent">Recently Updated</option>
            </select>
          </div>

          {/* Grid/List layout switcher */}
          <div className="inline-flex items-center rounded-lg border border-border p-1 bg-card shadow-sm h-10">
            <button
              onClick={() => setViewMode("grid")}
              className={`p-1.5 rounded-md transition-colors ${
                viewMode === "grid" 
                  ? "bg-secondary text-foreground" 
                  : "text-muted-foreground/60 hover:text-foreground"
              }`}
              aria-label="Grid View"
            >
              <Grid className="w-4.5 h-4.5" />
            </button>
            <button
              onClick={() => setViewMode("list")}
              className={`p-1.5 rounded-md transition-colors ${
                viewMode === "list" 
                  ? "bg-secondary text-foreground" 
                  : "text-muted-foreground/60 hover:text-foreground"
              }`}
              aria-label="List View"
            >
              <List className="w-4.5 h-4.5" />
            </button>
          </div>

          {/* Filters Toggle Button */}
          <button
            onClick={() => setShowFiltersPanel(!showFiltersPanel)}
            className={`inline-flex items-center gap-1.5 h-10 px-4 rounded-lg border text-xs font-mono transition-all shadow-sm ${
              showFiltersPanel 
                ? "bg-black dark:bg-white border-black dark:border-white text-white dark:text-black" 
                : "bg-card border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            <SlidersHorizontal className="w-4 h-4" />
            <span>Filters</span>
          </button>
        </div>
      </div>

      {/* Expanded filters panel */}
      {showFiltersPanel && (
        <div className="p-5 border border-border bg-card/45 rounded-xl grid grid-cols-1 sm:grid-cols-2 gap-6 animate-fadeIn">
          {/* Filter Option 1 */}
          <div className="space-y-2">
            <h4 className="text-xs font-mono uppercase tracking-wider text-muted-foreground/60 font-bold">
              Content Density
            </h4>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setSelectedCategory(null)}
                className={`px-3 py-1.5 rounded-lg text-xs border ${
                  !selectedCategory 
                    ? "border-black/30 dark:border-white/30 bg-black/5 dark:bg-white/5 text-black dark:text-white font-medium" 
                    : "border-border bg-card/60 text-muted-foreground hover:text-foreground"
                }`}
              >
                All Volumes
              </button>
              <button
                onClick={() => {
                  // filter categories containing at least 1 article
                  const withArticles = cleanCategories.filter(c => c.totalCount > 0);
                  if (withArticles.length > 0) {
                    setSelectedCategory(withArticles[0].slug);
                  }
                }}
                className={`px-3 py-1.5 rounded-lg text-xs border border-border bg-card/60 text-muted-foreground hover:text-foreground`}
              >
                Active Topics Only
              </button>
            </div>
          </div>

          {/* Filter Option 2 */}
          <div className="space-y-2">
            <h4 className="text-xs font-mono uppercase tracking-wider text-muted-foreground/60 font-bold">
              Animation Preference
            </h4>
            <div className="flex gap-2 text-xs font-mono text-muted-foreground">
              <span>System Prefers Reduced Motion: </span>
              <span className={`font-bold uppercase ${shouldReduce ? "text-amber-500" : "text-emerald-500"}`}>
                {shouldReduce ? "Enabled (Fade only)" : "Disabled (Full spring motion)"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ── Horizontal Scrollable Category Filter Pills ── */}
      <div className="relative">
        <div className="flex items-center gap-2 overflow-x-auto pb-3 pt-1 scrollbar-none scroll-smooth">
          {pills.map((pill) => (
            <button
              key={pill.slug || "all"}
              onClick={() => setSelectedCategory(pill.slug)}
              className={`px-4 py-1.5 rounded-full text-xs font-medium tracking-wide border whitespace-nowrap transition-all duration-300 ${
                selectedCategory === pill.slug
                  ? "bg-black dark:bg-white border-black dark:border-white text-white dark:text-black shadow-sm shadow-black/10 dark:shadow-white/10"
                  : "bg-transparent text-muted-foreground border-black/10 dark:border-white/10 hover:bg-black/10 dark:hover:bg-white/10"
              }`}
            >
              {pill.name}
            </button>
          ))}
        </div>
        {/* Subtle horizontal gradient fades on overflow */}
        <div className="absolute right-0 top-0 bottom-3 w-8 pointer-events-none bg-gradient-to-l from-background to-transparent" />
        <div className="absolute left-0 top-0 bottom-3 w-8 pointer-events-none bg-gradient-to-r from-background to-transparent" />
      </div>

      {/* ── Staggered Animated Topics Grid/List ── */}
      <div className="space-y-6">
        <div className="border-b border-border/40 pb-3 flex items-center justify-between">
          <h2 className="text-xl font-bold tracking-tight font-serif text-foreground">
            {selectedCategory ? pills.find(p => p.slug === selectedCategory)?.name : "All Tech Categories"}
          </h2>
          <span className="text-xs font-mono text-muted-foreground/50">
            Showing {filteredAndSorted.length} of {cleanCategories.length} topics
          </span>
        </div>

        {rows.length > 0 ? (
          <TopicsGrid rows={rows} viewMode={viewMode} />
        ) : (
          <div className="text-center py-16 border border-border rounded-xl bg-card/20 shadow-sm animate-fadeIn">
            <Search className="w-10 h-10 mx-auto text-muted-foreground/30 mb-3" />
            <h3 className="text-sm font-semibold text-muted-foreground">No matching categories found</h3>
            <p className="text-xs text-muted-foreground/50 mt-1">
              Try adjusting your filter keyword or category selection.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

CategoryGrid.displayName = "CategoryGrid";
