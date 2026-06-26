import React from "react";
import Link from "next/link";
import { Link2, Layers, Shuffle, ArrowRight } from "lucide-react";

interface RelatedArticle {
  id: number;
  slug: string;
  title: string;
  source: string;
  relationType: "similar" | "topic" | "perspective";
}

interface SemanticRelatedProps {
  articles: RelatedArticle[];
}

export function SemanticRelated({ articles }: SemanticRelatedProps) {
  if (!articles || articles.length === 0) return null;

  const getIcon = (type: RelatedArticle["relationType"]) => {
    switch (type) {
      case "similar": return <Link2 className="w-3.5 h-3.5 text-blue-500" />;
      case "topic": return <Layers className="w-3.5 h-3.5 text-emerald-500" />;
      case "perspective": return <Shuffle className="w-3.5 h-3.5 text-amber-500" />;
    }
  };

  const getLabel = (type: RelatedArticle["relationType"]) => {
    switch (type) {
      case "similar": return "Similar Story";
      case "topic": return "Same Topic";
      case "perspective": return "Different Perspective";
    }
  };

  return (
    <div className="bg-card border border-border rounded-xl p-5 space-y-5">
      <div className="flex items-center justify-between border-b border-border/50 pb-4">
        <h3 className="font-sans font-bold text-sm text-foreground tracking-tight">
          Related Coverage
        </h3>
      </div>

      <div className="space-y-4">
        {articles.map((article) => (
          <Link 
            key={article.id} 
            href={`/articles/${article.slug}`}
            className="group block p-3 rounded-lg border border-border/50 bg-card/60 hover:bg-card transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
          >
            <div className="flex items-center gap-1.5 mb-2">
              {getIcon(article.relationType)}
              <span className="text-[10px] uppercase font-mono tracking-widest text-muted-foreground font-semibold">
                {getLabel(article.relationType)}
              </span>
            </div>
            
            <h4 className="font-sans font-bold text-sm text-foreground leading-snug group-hover:text-primary transition-colors line-clamp-2 mb-1">
              {article.title}
            </h4>
            
            <div className="flex items-center justify-between mt-2">
              <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
                {article.source}
              </span>
              <ArrowRight className="w-3.5 h-3.5 text-muted-foreground group-hover:text-primary transition-colors group-hover:translate-x-1" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
