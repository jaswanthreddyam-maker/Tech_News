"use client";

import React from "react";
import Link from "next/link";
import { m, useReducedMotion } from "framer-motion";
import { Clock, Calendar, ArrowUpRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { FeaturedArticle } from "./types";
import {
  getHeadlineVariants,
  getSummaryVariants,
  getPrimaryActionVariants,
} from "./carousel.animations";
import { MotionScales } from "@/design-system/motion/tokens";

interface HeroContentProps {
  article: FeaturedArticle;
  onPrimaryAction?: (article: FeaturedArticle, event: React.MouseEvent) => void;
}

export function HeroContent({
  article,
  onPrimaryAction,
}: HeroContentProps) {
  const shouldReduceMotion = !!useReducedMotion();

  const headlineVariants = getHeadlineVariants(shouldReduceMotion);
  const summaryVariants = getSummaryVariants();
  const primaryActionVariants = getPrimaryActionVariants();

  return (
    <div className="flex flex-col justify-center h-full min-h-[300px] py-4 lg:py-8">
      {/* Article Meta row */}
      <div className="flex flex-wrap items-center gap-3 text-xs font-mono uppercase tracking-wider text-muted-foreground mb-4">
        <Badge
          variant="outline"
          className="text-primary border-primary/30 bg-primary/5 rounded-full px-2.5 py-0.5 text-[10px]"
        >
          {article.category}
        </Badge>
        
        <span className="font-bold text-foreground/80">{article.source}</span>
        
        <span className="text-border/80">|</span>

        <div className="flex items-center gap-1 shrink-0">
          <Clock className="w-3.5 h-3.5" />
          <span>{article.readTime} MIN READ</span>
        </div>

        <span className="text-border/80">|</span>

        <div className="flex items-center gap-1 shrink-0">
          <Calendar className="w-3.5 h-3.5" />
          <time dateTime={article.publishedAt} suppressHydrationWarning>
            {new Date(article.publishedAt).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
              year: "numeric",
              timeZone: "UTC"
            })}
          </time>
        </div>
      </div>

      {/* Headline - Screen reader announcements polite live region */}
      <m.h2
        variants={headlineVariants}
        className="text-3xl md:text-4xl lg:text-5xl font-serif font-bold text-foreground leading-[1.15] tracking-tight mb-4 select-text"
        aria-live="polite"
      >
        <Link 
          href={`/articles/${article.slug}`}
          onClick={(e) => onPrimaryAction?.(article, e)}
          draggable={false}
          className="hover:text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
        >
          {article.title}
        </Link>
      </m.h2>

      {/* Summary */}
      <m.p
        variants={summaryVariants}
        className="text-muted-foreground text-sm md:text-base leading-relaxed mb-6 line-clamp-3 select-text"
      >
        {article.summary}
      </m.p>

      {/* CTA Primary Action */}
      <m.div variants={primaryActionVariants} className="mt-2">
        <m.div
          whileHover={{ scale: MotionScales.hover }}
          whileTap={{ scale: MotionScales.tap }}
          className="inline-flex"
        >
          <Link
            href={`/articles/${article.slug}`}
            prefetch={true}
            onClick={(e) => onPrimaryAction?.(article, e)}
            draggable={false}
            className="inline-flex items-center gap-1.5 text-xs font-mono uppercase tracking-widest text-foreground hover:text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2 py-1"
          >
            Read Full Intelligence <ArrowUpRight className="w-4 h-4" />
          </Link>
        </m.div>
      </m.div>
    </div>
  );
}

HeroContent.displayName = "HeroContent";
