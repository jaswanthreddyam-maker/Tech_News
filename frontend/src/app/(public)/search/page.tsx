"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { SearchFilters as FiltersType } from "@/lib/api/search/types";
import {
  SearchFilters,
  SemanticSearchResults,
  WhyTheseResults,
} from "@/components/search";
import { saveSearchHistory } from "@/lib/api/search/history";

import { notFound } from "next/navigation";

export default function SearchPage() {
  if (true as boolean) {
    notFound();
  }
  return (
    <div className="max-w-screen-2xl mx-auto px-4 md:px-6 py-8 md:py-12">
      <Suspense fallback={<div>Loading search...</div>}>
        <SearchPageContent />
      </Suspense>
    </div>
  );
}

function SearchPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  
  const initialQuery = searchParams.get("q") || "";
  const [query, setQuery] = useState(initialQuery);
  const [activeQuery, setActiveQuery] = useState(initialQuery);
  
  const [filters, setFilters] = useState<FiltersType>({
    matchType: "hybrid",
    sort: "relevance",
    category: "all",
    dateRange: "all",
    credibility: undefined,
    aiConfidence: undefined,
  });

  // Sync state if URL changes (e.g. back button)
  useEffect(() => {
    const q = searchParams.get("q") || "";
    setQuery(q);
    setActiveQuery(q);

    // Sync filters from URL params (e.g. mode, category)
    const categoryParam = searchParams.get("category");
    const modeParam = searchParams.get("mode") || searchParams.get("matchType");
    
    setFilters(prev => ({
      ...prev,
      category: categoryParam || "all",
      matchType: (modeParam === "semantic" || modeParam === "keyword" || modeParam === "hybrid" || modeParam === "all") 
        ? (modeParam as any)
        : "hybrid",
    }));
  }, [searchParams]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    saveSearchHistory(query);
    setActiveQuery(query);
    
    const params = new URLSearchParams(searchParams.toString());
    params.set("q", query.trim());
    router.push(`/search?${params.toString()}`);
  };

  return (
    <div className="space-y-8">
      {/* Search Header */}
      <div className="max-w-3xl mx-auto text-center space-y-4 mb-12">
        <h1 className="text-3xl md:text-5xl font-bold tracking-tight">Semantic Search</h1>
        <p className="text-muted-foreground">
          Find deep connections across our AI newsroom using natural language.
        </p>
        <form onSubmit={handleSearchSubmit} className="relative mt-8 max-w-2xl mx-auto">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
          <input
            type="text"
            className="w-full h-14 pl-12 pr-4 rounded-full bg-card border border-border/50 text-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all shadow-sm"
            placeholder="Search Tech News..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </form>
      </div>

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Filters Sidebar */}
        <aside className="w-full lg:w-64 shrink-0 space-y-6">
          <div className="sticky top-20 bg-card/30 p-6 rounded-xl border border-border/50">
            <h2 className="text-lg font-bold mb-6">Filters</h2>
            <SearchFilters filters={filters} onChange={setFilters} />
          </div>
        </aside>

        {/* Results Area */}
        <div className="flex-1 min-w-0">
          {activeQuery ? (
            <>
              <WhyTheseResults />
              <SemanticSearchResults query={activeQuery} filters={filters} />
            </>
          ) : (
            <div className="py-24 text-center text-muted-foreground">
              <Search className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>Type a query to begin searching</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
