"use client";

import React, { useMemo } from "react";
import Link from "next/link";
import { useRecommendations } from "@/hooks/useRecommendations";
import { usePersonalization } from "@/components/providers/PersonalizationProvider";
import { StoryCard } from "@/components/common/StoryCard";
import { EmptyState, EmptyIllustration, EmptyAction } from "@/components/common/EmptyState";
import { Sparkles, Loader2, RefreshCw, SlidersHorizontal } from "lucide-react";
import { useDashboard } from "@/components/providers/DashboardProvider";

export function RecommendationsList() {
  const { readingHistory, recommendationSettings } = usePersonalization();
  const { setActiveTab } = useDashboard();

  const { data: recommendations, isLoading, refetch, isFetching } = useRecommendations({
    limit: 15,
    mode: "history",
    enabled: true,
  });

  const filteredRecommendations = useMemo(() => {
    if (!recommendations || recommendations.length === 0) return [];

    let list = [...recommendations];

    // 1. Hide read articles filter
    if (recommendationSettings.hideReadArticles) {
      const readIds = new Set(readingHistory.map((h) => h.articleId));
      list = list.filter((art) => !readIds.has(Number(art.id)));
    }

    // 2. Prefer trusted sources
    if (recommendationSettings.preferTrustedSources) {
      const trusted = ["Reuters", "Associated Press", "Bloomberg", "TechCrunch", "The Verge", "Ars Technica", "MIT Technology Review"];
      list.sort((a, b) => {
        const aTrusted = trusted.some((t) => (a.source_name || "").includes(t));
        const bTrusted = trusted.some((t) => (b.source_name || "").includes(t));
        if (aTrusted && !bTrusted) return -1;
        if (!aTrusted && bTrusted) return 1;
        return 0;
      });
    }

    // 3. Priority sort
    if (recommendationSettings.prioritize === "freshness") {
      list.sort((a, b) => {
        const dateA = a.published_at ? new Date(a.published_at).getTime() : 0;
        const dateB = b.published_at ? new Date(b.published_at).getTime() : 0;
        return dateB - dateA;
      });
    }

    return list;
  }, [recommendations, recommendationSettings, readingHistory]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-16">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!filteredRecommendations || filteredRecommendations.length === 0) {
    return (
      <EmptyState size="lg">
        <EmptyIllustration
          icon={Sparkles}
          title="No recommendations"
          description="We are computing your personalized feed."
        />
        <EmptyAction
          primaryAction={
            <Link
              href="/"
              className="px-4 py-2 bg-primary text-primary-foreground rounded-full text-sm font-medium hover:bg-primary/90 transition-colors inline-block"
            >
              Explore News to Train Algorithm
            </Link>
          }
          secondaryAction={
            <button
              onClick={() => setActiveTab("preferences")}
              className="px-4 py-2 bg-card border border-border/60 text-foreground rounded-full text-sm font-medium hover:bg-muted transition-colors inline-flex items-center gap-1.5 cursor-pointer"
            >
              <SlidersHorizontal className="w-4 h-4" />
              Adjust Preferences
            </button>
          }
        />
      </EmptyState>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 pb-2 border-b border-border/40">
        <div className="flex items-center gap-2">
          <span className="text-sm font-mono text-muted-foreground">
            Personalized Feed • Priority:
          </span>
          <span className="text-xs font-mono uppercase tracking-wider text-primary font-bold bg-primary/10 px-2 py-0.5 rounded-full border border-primary/20">
            {recommendationSettings.prioritize}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setActiveTab("preferences")}
            className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 font-mono uppercase tracking-wider transition-colors cursor-pointer"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>Preferences</span>
          </button>

          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="text-xs text-muted-foreground hover:text-primary inline-flex items-center gap-1.5 font-mono uppercase tracking-wider transition-colors disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? "animate-spin text-primary" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {filteredRecommendations.map((art) => (
          <StoryCard
            key={art.id}
            article={art as any}
            recommendation={{
              reasons: art.reasons,
            }}
          />
        ))}
      </div>
    </div>
  );
}
