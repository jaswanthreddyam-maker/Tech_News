"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Search, ArrowRight, Clock, TrendingUp } from "lucide-react";

interface SearchOverlayProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const recentSearches = [
  "NVIDIA Blackwell",
  "Apple AI",
  "Humanoid robots",
];

const suggestedSearches = [
  "Latest AI breakthroughs",
  "Companies investing in robotics",
  "Startup funding news",
  "Cybersecurity threats 2026",
];

export function SearchOverlay({ open, onOpenChange }: SearchOverlayProps) {
  const router = useRouter();
  const [query, setQuery] = React.useState("");
  const inputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (open) {
      // Small delay to ensure dialog is rendered
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery("");
    }
  }, [open]);

  const handleSearch = (searchQuery: string) => {
    if (!searchQuery.trim()) return;
    onOpenChange(false);
    router.push(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch(query);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[560px] p-0 gap-0 rounded-dialog border-border/50 bg-background/95 backdrop-blur-xl overflow-hidden">
        {/* Search Input */}
        <div className="flex items-center border-b border-border px-4">
          <Search className="h-4 w-4 text-muted-foreground shrink-0" />
          <Input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask Tech News..."
            className="border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 h-12 text-sm placeholder:text-muted-foreground"
          />
        </div>

        {/* Suggestions */}
        <div className="max-h-[320px] overflow-y-auto p-2">
          {/* Recent */}
          {recentSearches.length > 0 && (
            <div className="px-2 py-1.5">
              <p className="text-xs font-medium text-muted-foreground mb-1.5">Recent</p>
              {recentSearches.map((term) => (
                <button
                  key={term}
                  onClick={() => handleSearch(term)}
                  className="flex items-center gap-3 w-full px-2 py-2 text-sm text-foreground/80 hover:bg-secondary rounded-button transition-colors duration-hover"
                >
                  <Clock className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                  <span className="flex-1 text-left">{term}</span>
                  <ArrowRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 group-hover:opacity-100" />
                </button>
              ))}
            </div>
          )}

          {/* Suggested */}
          <div className="px-2 py-1.5">
            <p className="text-xs font-medium text-muted-foreground mb-1.5">Suggested</p>
            {suggestedSearches.map((term) => (
              <button
                key={term}
                onClick={() => handleSearch(term)}
                className="flex items-center gap-3 w-full px-2 py-2 text-sm text-foreground/80 hover:bg-secondary rounded-button transition-colors duration-hover"
              >
                <TrendingUp className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                <span className="flex-1 text-left">{term}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Footer hint */}
        <div className="border-t border-border px-4 py-2 flex items-center justify-between text-[10px] text-muted-foreground font-mono">
          <span>Powered by Semantic Search</span>
          <span>Press ↵ to search</span>
        </div>
      </DialogContent>
    </Dialog>
  );
}
