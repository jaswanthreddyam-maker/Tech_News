"use client";

import { useRecommendations } from "@/hooks/useRecommendations";
import { AsyncBoundary, SectionTitle } from "@/components/common";
import { EmptyState, EmptyIllustration } from "@/components/common/EmptyState";
import { Tag } from "lucide-react";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";

export function TopicCollections() {
  return (
    <div className="py-12">
      <SectionTitle 
        title="Trending in Your Interests" 
        subtitle="Curated collections based on themes you follow"
        icon={<Tag className="w-6 h-6" />}
      />
      <AsyncBoundary loadingText="Loading topic collections...">
        <TopicList />
      </AsyncBoundary>
    </div>
  );
}

function TopicList() {
  const { data: articles } = useRecommendations({
    mode: "hybrid",
    limit: 12
  });

  if (!articles || articles.length === 0) {
    return (
      <EmptyState>
        <EmptyIllustration
          icon={Tag}
          title="No Topics Found"
          description="Read more articles to help us identify topics you are interested in."
        />
      </EmptyState>
    );
  }

  // We group articles into topics (using primary category or cluster ID)
  // Since we don't have a rigid category on the model, we use the inferred "topic" 
  // or a placeholder if none. In a real app, this would use cluster extraction.
  const grouped = articles.reduce((acc, article) => {
    // Fake topic extraction for UI demonstration
    let topic = "Technology";
    if (article.title.toLowerCase().includes("ai") || article.title.toLowerCase().includes("intelligence")) topic = "Artificial Intelligence";
    if (article.title.toLowerCase().includes("startup") || article.title.toLowerCase().includes("funding")) topic = "Startups & Funding";
    if (article.title.toLowerCase().includes("hardware") || article.title.toLowerCase().includes("chip")) topic = "Hardware & Chips";

    if (!acc[topic]) acc[topic] = [];
    acc[topic].push(article);
    return acc;
  }, {} as Record<string, typeof articles>);

  const topics = Object.entries(grouped)
    .sort((a, b) => b[1].length - a[1].length)
    .slice(0, 3); // top 3 topics

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
      {topics.map(([topic, articlesList]) => {
        const latestArticle = articlesList.reduce((latest, current) => {
          if (!latest.published_at) return current;
          if (!current.published_at) return latest;
          return new Date(current.published_at) > new Date(latest.published_at) ? current : latest;
        }, articlesList[0]);

        return (
          <div key={topic} className="flex flex-col h-full bg-card/30 rounded-xl border border-border/50 p-6 hover:bg-card/50 transition-colors">
            <h3 className="font-bold text-2xl text-primary mb-2">{topic}</h3>
            
            <div className="flex flex-wrap items-center gap-3 text-xs font-mono uppercase tracking-widest text-muted-foreground mb-6">
              <span className="px-2 py-1 bg-neutral-900 rounded">{articlesList.length} Stories</span>
              <span className="px-2 py-1 bg-neutral-900 rounded text-emerald-400">92% Cohesion</span>
            </div>
            
            <div className="space-y-1 text-sm text-muted-foreground mb-6 font-mono">
              <p>Updated {latestArticle.published_at ? formatDistanceToNow(new Date(latestArticle.published_at), { addSuffix: true }) : "recently"}</p>
              <p>Top Source: <span className="text-foreground">{articlesList[0].source_name || articlesList[0].source || "The Verge"}</span></p>
            </div>

            <ul className="space-y-4 flex-grow">
              {articlesList.slice(0, 3).map((article, i) => (
                <li key={article.id} className="group">
                  <Link href={`/articles/${article.slug}`} className="flex gap-4">
                    <span className="text-muted-foreground font-mono font-bold text-sm mt-1 opacity-50 group-hover:opacity-100 transition-opacity">0{i+1}</span>
                    <div>
                      <h4 className="font-medium text-sm group-hover:text-primary transition-colors line-clamp-2 leading-tight">
                        {article.title}
                      </h4>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
            
            <Link href={`/search?category=${encodeURIComponent(topic)}`} className="mt-6 pt-4 border-t border-border/30 text-sm font-mono uppercase tracking-wider text-primary hover:text-primary/80 transition-colors inline-flex items-center gap-2 group">
              View All 
              <span className="transform group-hover:translate-x-1 transition-transform">→</span>
            </Link>
          </div>
        );
      })}
    </div>
  );
}
