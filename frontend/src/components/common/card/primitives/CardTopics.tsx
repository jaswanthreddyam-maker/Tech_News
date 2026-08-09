"use client";

import React from "react";

interface CardTopicsProps {
  topics?: string[] | null;
  maxDisplay?: number;
  className?: string;
}

export function CardTopics({ topics, maxDisplay = 3, className = "" }: CardTopicsProps) {
  if (!topics || topics.length === 0) return null;

  const displayTopics = topics.slice(0, maxDisplay);
  const remaining = topics.length - maxDisplay;

  return (
    <div className={`flex flex-wrap items-center gap-1.5 font-mono text-[11px] text-muted-foreground/90 ${className}`}>
      <span className="text-muted-foreground/70 font-semibold uppercase tracking-wider text-[10px]">
        Covering:
      </span>
      {displayTopics.map((topic, i) => (
        <span
          key={i}
          className="bg-white/[0.04] text-foreground/80 border border-white/10 px-2 py-0.5 rounded-full font-medium"
        >
          {topic}
        </span>
      ))}
      {remaining > 0 && (
        <span className="text-muted-foreground/60 text-[10px]">
          +{remaining} more
        </span>
      )}
    </div>
  );
}
