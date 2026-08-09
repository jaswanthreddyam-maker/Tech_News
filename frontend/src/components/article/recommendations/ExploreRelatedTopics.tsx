"use client";

import React, { useMemo } from "react";
import { Sparkles } from "lucide-react";
import { CanonicalArticle } from "@/domains/article";
import { buildTopicClusters, TopicCluster } from "@/domains/topic";
import { TopicCard } from "@/components/common/card/TopicCard";

interface ExploreRelatedTopicsProps {
  currentArticle?: CanonicalArticle | null;
  allArticles?: CanonicalArticle[] | null;
  className?: string;
}

export function ExploreRelatedTopics({
  currentArticle,
  allArticles,
  className = "",
}: ExploreRelatedTopicsProps) {
  const clusters = useMemo<TopicCluster[]>(() => {
    if (!allArticles || allArticles.length === 0) return [];
    
    const computed = buildTopicClusters(allArticles);

    if (!currentArticle) return computed.slice(0, 6);

    const currentTopics = new Set((currentArticle.primaryTopics || []).map((t) => t.toLowerCase()));

    // Boost clusters matching current article's primary topics
    return computed
      .map((cluster) => {
        const isMatch = currentTopics.has(cluster.topic.toLowerCase());
        return {
          ...cluster,
          score: cluster.score + (isMatch ? 50 : 0),
        };
      })
      .sort((a, b) => b.score - a.score)
      .slice(0, 6);
  }, [currentArticle, allArticles]);

  if (clusters.length === 0) return null;

  return (
    <section className={`space-y-6 pt-10 border-t border-border/40 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-primary font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-primary" strokeWidth={1.75} />
            <span>Topic Curation</span>
          </div>
          <h3 className="text-2xl font-bold font-serif text-foreground">
            Explore Related Topics
          </h3>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {clusters.map((cluster) => (
          <TopicCard key={cluster.slug} cluster={cluster} />
        ))}
      </div>
    </section>
  );
}
