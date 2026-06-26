"use client";

import React, { useState } from "react";
import { Sparkles, ChevronDown, ChevronUp } from "lucide-react";

interface AISummaryCardProps {
  summary: string;
}

export function AISummaryCard({ summary }: AISummaryCardProps) {
  const [isOpen, setIsOpen] = useState(true);

  if (!summary) return null;

  return (
    <div className="bg-card border border-border rounded-xl overflow-hidden">
      {/* Toggle Header */}
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 text-left transition-colors hover:bg-accent/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
      >
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary animate-pulse" />
          <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
            Executive Brief
          </span>
        </div>
        {isOpen ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        )}
      </button>

      {/* Collapsible Content */}
      {isOpen && (
        <div className="p-5 pt-0 border-t border-border/30">
          <p className="text-sm text-muted-foreground leading-relaxed font-sans mt-3">
            {summary}
          </p>
        </div>
      )}
    </div>
  );
}
