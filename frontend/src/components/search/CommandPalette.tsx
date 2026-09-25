"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { useAnalytics } from "@/components/providers/AnalyticsProvider";
import { Newspaper, ArrowRight, Loader2 } from "lucide-react";
import { fetchKeywordSearch } from "@/lib/api/search/keyword";
import { KeywordSearchResult } from "@/lib/api/search/types";

export function CommandPalette({ onSelect }: { onSelect: () => void }) {
  const router = useRouter();
  const { track } = useAnalytics();
  const [search, setSearch] = React.useState("");
  const [searchResults, setSearchResults] = React.useState<KeywordSearchResult[]>([]);
  const [isSearching, setIsSearching] = React.useState(false);

  React.useEffect(() => {
    const trimmed = search.trim();
    if (!trimmed) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }

    setIsSearching(true);
    const timer = setTimeout(() => {
      fetchKeywordSearch(trimmed, undefined, 8)
        .then((res) => {
          const articles = (res || []).filter(
            (r) => r.type === "article" || !r.type
          );
          setSearchResults(articles);
          setIsSearching(false);
        })
        .catch((err) => {
          console.error("Search fetch error:", err);
          setSearchResults([]);
          setIsSearching(false);
        });
    }, 200);

    return () => clearTimeout(timer);
  }, [search]);

  const handleArticleSelect = (result: KeywordSearchResult) => {
    track("Article Opened", { articleId: String(result.id) });
    const targetSlug = result.url || String(result.id);
    router.push(`/articles/${targetSlug}`);
    onSelect();
  };

  const handleViewAll = () => {
    if (!search.trim()) return;
    track("Search Executed", { query: search.trim() });
    router.push(`/search?q=${encodeURIComponent(search.trim())}`);
    onSelect();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && search.trim() && searchResults.length === 0) {
      e.preventDefault();
      handleViewAll();
    }
  };

  const hasQuery = search.trim().length > 0;

  return (
    <Command
      shouldFilter={false}
      className="rounded-2xl border shadow-2xl sm:max-w-2xl bg-neutral-950/95 backdrop-blur-2xl border-white/10 overflow-hidden"
    >
      <CommandInput
        placeholder="Search tech news articles..."
        value={search}
        onValueChange={setSearch}
        onKeyDown={handleKeyDown}
        className="text-base text-foreground placeholder:text-muted-foreground/60 h-14"
      />

      {/* Only show content under the searchbar when the user types a query */}
      {hasQuery && (
        <CommandList className="max-h-[65vh] overflow-y-auto p-2 scrollbar-thin">
          {isSearching && (
            <div className="py-10 flex flex-col items-center justify-center gap-2.5 text-xs font-mono text-muted-foreground animate-in fade-in duration-150">
              <Loader2 className="w-5 h-5 animate-spin text-primary" />
              <span>Searching published articles...</span>
            </div>
          )}

          {!isSearching && searchResults.length === 0 && (
            <CommandEmpty>
              <div className="py-10 text-center space-y-2 animate-in fade-in duration-150">
                <p className="font-mono text-sm text-foreground font-medium">
                  No articles found for &quot;{search}&quot;
                </p>
                <p className="text-xs font-mono text-muted-foreground">
                  Try broader terms like &quot;AI&quot;, &quot;Google&quot;, &quot;Microsoft&quot;, or &quot;Chips&quot;
                </p>
                <div className="pt-2">
                  <button
                    type="button"
                    onClick={handleViewAll}
                    className="text-xs font-mono text-primary hover:underline font-semibold cursor-pointer"
                  >
                    View full archive search &rarr;
                  </button>
                </div>
              </div>
            </CommandEmpty>
          )}

          {!isSearching && searchResults.length > 0 && (
            <>
              <CommandGroup heading={`Articles matching "${search}"`}>
                {searchResults.map((result) => (
                  <CommandItem
                    key={`article-${result.id}`}
                    value={`${result.id} ${result.title}`}
                    onSelect={() => handleArticleSelect(result)}
                    className="flex items-start gap-3 p-3 rounded-xl cursor-pointer hover:bg-white/[0.08] data-[selected=true]:bg-white/[0.1] transition-all group border border-transparent hover:border-white/10"
                  >
                    <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 text-primary shrink-0 mt-0.5 group-hover:bg-primary/20 group-hover:scale-105 transition-all">
                      <Newspaper className="w-4 h-4" />
                    </div>
                    <div className="flex flex-col min-w-0 flex-1 space-y-1">
                      <span className="text-sm font-semibold text-foreground line-clamp-1 group-hover:text-primary transition-colors">
                        {result.title}
                      </span>
                      {result.description && (
                        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                          {result.description}
                        </p>
                      )}
                      {result.date && (
                        <div className="flex items-center gap-2 pt-0.5 text-[11px] font-mono text-muted-foreground/70">
                          <span>
                            {new Date(result.date).toLocaleDateString([], {
                              month: "short",
                              day: "numeric",
                              year: "numeric",
                            })}
                          </span>
                          <span>·</span>
                          <span className="text-primary/80 font-medium">Read Story</span>
                        </div>
                      )}
                    </div>
                    <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all shrink-0 self-center ml-2 opacity-50 group-hover:opacity-100" />
                  </CommandItem>
                ))}
              </CommandGroup>

              {/* Bottom Navigation Shortcut */}
              <div className="mt-2 pt-2 border-t border-white/10 flex items-center justify-between px-2 py-1 text-xs font-mono text-muted-foreground">
                <span className="text-[11px]">
                  Use <kbd className="px-1.5 py-0.5 rounded bg-white/10 text-[10px] text-foreground font-mono">↑</kbd> <kbd className="px-1.5 py-0.5 rounded bg-white/10 text-[10px] text-foreground font-mono">↓</kbd> to navigate, <kbd className="px-1.5 py-0.5 rounded bg-white/10 text-[10px] text-foreground font-mono">↵</kbd> to open
                </span>
                <button
                  type="button"
                  onClick={handleViewAll}
                  className="text-xs font-mono text-primary hover:underline font-semibold flex items-center gap-1 cursor-pointer"
                >
                  Full results page &rarr;
                </button>
              </div>
            </>
          )}
        </CommandList>
      )}
    </Command>
  );
}
