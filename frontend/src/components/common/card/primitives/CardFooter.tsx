"use client";

import React from "react";
import { ArrowUpRight, Bookmark } from "lucide-react";

interface CardFooterProps {
  sourceName?: string | null;
  className?: string;
}

export function CardFooter({ sourceName, className = "" }: CardFooterProps) {
  return (
    <div className={`flex items-center justify-between pt-2 text-xs font-mono border-t border-border/40 ${className}`}>
      <span className="text-muted-foreground/70 font-medium">
        {sourceName || "Tech News Today"}
      </span>

      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        <button
          type="button"
          aria-label="Bookmark article"
          onClick={(e) => {
            e.stopPropagation();
            e.preventDefault();
          }}
          className="p-1 text-muted-foreground/60 hover:text-foreground transition-colors"
        >
          <Bookmark className="w-3.5 h-3.5" />
        </button>

        <span className="flex items-center text-primary text-[11px] font-semibold">
          Read
          <ArrowUpRight className="w-3 h-3 ml-0.5 transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform duration-200" />
        </span>
      </div>
    </div>
  );
}
