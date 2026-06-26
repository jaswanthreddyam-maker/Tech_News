"use client";

import { useRecommendations } from "@/hooks/useRecommendations";
import { AsyncBoundary, SectionTitle } from "@/components/common";
import { EmptyState, EmptyIllustration } from "@/components/common/EmptyState";
import { StoryCard } from "@/components/common/StoryCard";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { RecommendationReasonBadges } from "./RecommendationReasonBadges";
import { Sparkles, BookOpen } from "lucide-react";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import Image from "next/image";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import Link from "next/link";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { formatDistanceToNow } from "date-fns";

export function ForYouGrid() {
  return (
    <div className="py-12">
      <SectionTitle 
        title="For You" 
        subtitle="Personalized recommendations based on your reading history"
        icon={<Sparkles className="w-6 h-6" />}
      />
      <AsyncBoundary loadingText="Curating your personalized feed...">
        <ForYouList />
      </AsyncBoundary>
    </div>
  );
}

function ForYouList() {
  const { data: articles } = useRecommendations({
    mode: "history",
    limit: 6
  });

  if (!articles || articles.length === 0) {
    return (
      <EmptyState>
        <EmptyIllustration
          icon={BookOpen}
          title="Start Reading"
          description="Read a few articles to start getting personalized recommendations tailored to your interests."
        />
      </EmptyState>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 overflow-x-auto pb-4 snap-x sm:snap-none">
      {articles.map(article => (
        <div key={article.id} className="snap-center shrink-0 w-[85vw] sm:w-auto">
          <StoryCard 
            article={article}
            recommendation={{ reasons: article.reasons as any }}
          />
        </div>
      ))}
    </div>
  );
}
