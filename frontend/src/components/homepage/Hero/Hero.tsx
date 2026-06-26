"use client";

import { useHeroArticle } from "@/components/hooks/articles/useArticles";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Clock, ArrowUpRight, BrainCircuit } from "lucide-react";
import Link from "next/link";
import { ArticleThumbnail } from "@/components/common/ArticleThumbnail";

export function HeroSection() {
  const { data, isLoading, error } = useHeroArticle();

  if (isLoading) return <Skeleton className="w-full h-[500px]" />;
  if (error || !data || !data.data || data.data.length === 0) return null;

  const article = data.data[0];

  return (
    <article className="group relative grid grid-cols-1 md:grid-cols-2 gap-6 bg-card border border-border overflow-hidden">
      {/* Content (Rendered First for LCP) */}
      <div className="flex flex-col justify-center p-6 lg:p-10 order-2 md:order-1">
        <div className="flex items-center gap-4 text-xs font-mono text-muted-foreground mb-4">
          <span className="flex items-center gap-1.5 uppercase tracking-wider">
            {article.source}
          </span>
          <span>|</span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            3 MIN READ
          </span>
          <span>|</span>
          <span suppressHydrationWarning>{new Date(article.published_at).toLocaleDateString('en-US', { timeZone: 'UTC' })}</span>
        </div>

        <Link href={`/articles/${article.slug}`} className="block group/link">
          <h2 className="text-3xl lg:text-5xl font-serif font-bold text-foreground mb-4 leading-[1.1] group-hover/link:text-primary transition-colors">
            {article.title}
          </h2>
        </Link>

        <p className="text-muted-foreground text-sm lg:text-base leading-relaxed mb-6 line-clamp-3">
          {article.summary}
        </p>

        {/* Why this matters (AI Insight) */}
        {article.why_this_matters && article.why_this_matters.length > 0 && (
          <div className="mt-auto pt-6 border-t border-border">
            <div className="flex items-center gap-2 mb-3">
              <BrainCircuit className="w-4 h-4 text-primary" />
              <h3 className="text-xs font-mono font-bold tracking-widest text-primary uppercase">
                Why this matters
              </h3>
            </div>
            <ul className="space-y-2">
              {article.why_this_matters.map((point, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-foreground/80">
                  <span className="block mt-1.5 w-1 h-1 rounded-full bg-primary/50 shrink-0" />
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-8 pt-4">
          <Link 
            href={`/articles/${article.slug}`}
            className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-foreground hover:text-primary transition-colors"
          >
            Read Full Intelligence <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Image Container */}
      <div className="relative aspect-[16/9] w-full h-full min-h-[300px] overflow-hidden bg-neutral-900 order-1 md:order-2">
        <ArticleThumbnail 
          article={article}
          className="w-full h-full"
          imgClassName="object-cover transition-opacity duration-700 ease-in-out"
          sizes="(max-width: 768px) 100vw, 50vw"
          priority={true}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent pointer-events-none" />
        
        {/* Badges Overlay */}
        <div className="absolute top-4 right-4 md:right-auto md:left-4 flex gap-2">
          <Badge variant="default" className="bg-primary text-primary-foreground">
            {article.category}
          </Badge>
          {article.ai_confidence && article.ai_confidence > 90 && (
            <Badge variant="outline" className="bg-black/50 backdrop-blur-sm border-emerald-500/30 text-emerald-400">
              {article.ai_confidence}% Confidence
            </Badge>
          )}
        </div>
      </div>
    </article>
  );
}
