"use client";

import React from "react";
import Link from "next/link";
import { Tag, ArrowRight, Layers } from "lucide-react";
import { TopicCluster } from "@/domains/topic";

interface TopicCardProps {
  cluster: TopicCluster;
  className?: string;
}

export function TopicCard({ cluster, className = "" }: TopicCardProps) {
  return (
    <Link
      href={`/topics/${cluster.slug}`}
      className={`group block relative rounded-xl bg-card/50 hover:bg-card border border-border/50 hover:border-white/20 p-4 transition-all duration-300 shadow-sm hover:shadow-md h-[135px] flex flex-col justify-between ${className}`}
    >
      <div>
        {/* Title & Arrow Row */}
        <div className="flex items-center justify-between gap-2 mb-1">
          <div className="flex items-center gap-2 min-w-0">
            <Tag className="w-3.5 h-3.5 text-primary shrink-0" strokeWidth={1.75} />
            <h4 className="font-serif font-bold text-sm text-foreground group-hover:text-primary transition-colors truncate">
              {cluster.topic}
            </h4>
          </div>

          <ArrowRight className="w-4 h-4 text-muted-foreground/50 group-hover:text-primary group-hover:translate-x-1 transition-all shrink-0" strokeWidth={1.75} />
        </div>

        {/* Story Count Badge */}
        <div className="flex items-center gap-1.5 text-[11px] font-mono text-muted-foreground/70 pl-5">
          <Layers className="w-3 h-3 text-muted-foreground/50" />
          <span>{cluster.storyCount} {cluster.storyCount === 1 ? "story" : "stories"}</span>
        </div>
      </div>

      {/* Latest Article Headline Snippet */}
      {cluster.latestArticle && (
        <div className="pt-2 border-t border-border/40 text-xs text-muted-foreground/80 font-sans line-clamp-1 truncate">
          <span className="font-mono text-[10px] text-muted-foreground/50 uppercase tracking-wider mr-1.5 font-bold">Latest:</span>
          {cluster.latestArticle.title}
        </div>
      )}
    </Link>
  );
}
