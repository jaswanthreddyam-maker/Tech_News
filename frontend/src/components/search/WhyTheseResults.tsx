"use client";

import { ChevronDown, Sparkles } from "lucide-react";
import { useState } from "react";

export function WhyTheseResults() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="mb-6 rounded-xl border border-border/50 bg-card/30 overflow-hidden">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-card/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary" />
          <span className="font-mono text-sm tracking-wide">Why these results?</span>
        </div>
        <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </button>
      
      {isOpen && (
        <div className="px-4 pb-4 pt-2 border-t border-border/30 text-sm text-muted-foreground bg-neutral-900/30">
          <ul className="space-y-2 mb-4">
            <li className="flex items-start gap-2">
              <span className="text-primary mt-1">•</span>
              <span>Ranked primarily by <strong>semantic similarity (60%)</strong> using our custom embedding pipeline.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary mt-1">•</span>
              <span>Boosted by <strong>keyword overlap (20%)</strong> to ensure exact phrasing is caught.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary mt-1">•</span>
              <span><strong>Freshness adjustment applied (10%)</strong> to prioritize breaking news.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary mt-1">•</span>
              <span><strong>Source credibility adjustment applied (10%)</strong> to prioritize highly trusted publishers.</span>
            </li>
          </ul>
          
          <div className="p-3 bg-card/50 rounded border border-border/30 font-mono text-xs">
            <span className="text-muted-foreground">Current search mode:</span>
            <div className="text-foreground mt-1 font-bold">Hybrid Semantic Search</div>
          </div>
        </div>
      )}
    </div>
  );
}
