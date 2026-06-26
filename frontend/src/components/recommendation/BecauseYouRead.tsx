"use client";

import { useRecommendations } from "@/hooks/useRecommendations";
import { AsyncBoundary, SectionTitle } from "@/components/common";
import { StoryCard } from "@/components/common/StoryCard";
import { Sparkles } from "lucide-react";

interface Props {
  articleId: number;
}

export function BecauseYouRead({ articleId }: Props) {
  return (
    <div className="mt-16 pt-8 border-t border-border/50">
      <SectionTitle 
        title="Because You Read..." 
        icon={<Sparkles className="w-6 h-6" />}
      />
      <AsyncBoundary loadingText="Finding similar articles...">
        <BecauseYouReadList articleId={articleId} />
      </AsyncBoundary>
    </div>
  );
}

function BecauseYouReadList({ articleId }: { articleId: number }) {
  const { data: articles } = useRecommendations({
    mode: "article",
    currentArticleId: articleId,
    limit: 3
  });

  if (!articles || articles.length === 0) {
    return null; // Don't show anything if no related articles found
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {articles.map(article => (
        <StoryCard 
          key={article.id}
          article={article}
          recommendation={{ reasons: article.reasons as any }}
        />
      ))}
    </div>
  );
}
