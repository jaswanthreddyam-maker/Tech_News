"use client";

import React from "react";
import Link from "next/link";
import { m } from "framer-motion";
import { Sparkles } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion";
import { FeaturedArticle } from "./types";
import { getSidebarVariants } from "./carousel.animations";

interface HeroInsightsListProps {
  articles: FeaturedArticle[];
  onInsightClick?: (article: FeaturedArticle) => void;
}

export function HeroInsightsList({
  articles,
  onInsightClick,
}: HeroInsightsListProps) {
  if (!articles || articles.length === 0) {
    return (
      <div className="text-xs text-muted-foreground py-6 text-center">
        No insights available.
      </div>
    );
  }

  return (
    <ul className="space-y-4">
      {articles.slice(0, 4).map((art) => (
        <li
          key={art.id}
          className="group/item pb-3 border-b border-border/40 last:border-0 last:pb-0"
        >
          <Link
            href={`/articles/${art.slug}`}
            prefetch={false}
            onClick={() => onInsightClick?.(art)}
            className="block focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2 rounded"
          >
            <span className="text-[9px] font-mono uppercase tracking-wider text-primary font-bold block mb-1">
              {art.category}
            </span>
            <h4 className="font-serif font-bold text-sm text-foreground group-hover/item:text-primary transition-colors line-clamp-2 leading-snug">
              {art.title}
            </h4>
            <p className="text-xs text-muted-foreground line-clamp-2 mt-1 leading-normal">
              {art.summary}
            </p>
          </Link>
        </li>
      ))}
    </ul>
  );
}

HeroInsightsList.displayName = "HeroInsightsList";

interface HeroInsightsProps {
  editorPicks: FeaturedArticle[];
  latest: FeaturedArticle[];
  aiInsights: FeaturedArticle[];
  onInsightClick?: (article: FeaturedArticle) => void;
}

export function HeroInsights({
  editorPicks,
  latest,
  aiInsights,
  onInsightClick,
}: HeroInsightsProps) {
  const sidebarVariants = getSidebarVariants();

  return (
    <m.div
      variants={sidebarVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className="bg-card border border-border p-5 h-full flex flex-col relative overflow-hidden rounded-xl"
    >
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-24 h-24 bg-primary/5 blur-2xl rounded-full pointer-events-none" />

      {/* Header */}
      <div className="flex items-center gap-2 mb-4 border-b border-border/60 pb-3 flex-shrink-0">
        <Sparkles className="w-4.5 h-4.5 text-primary" />
        <h3 className="font-sans font-bold text-md text-foreground tracking-tight">
          Today&apos;s AI Insights
        </h3>
      </div>

      {/* Desktop / Tablet: Tabs */}
      <div className="hidden md:block flex-1 min-h-0">
        <Tabs defaultValue="editors-picks" className="w-full h-full flex flex-col">
          <TabsList className="grid grid-cols-3 bg-muted/40 p-0.5 h-8 border border-border/30 rounded-lg mb-4">
            <TabsTrigger
              value="editors-picks"
              className="text-[10px] md:text-xs font-mono font-semibold py-1 rounded-md"
            >
              Editor&apos;s
            </TabsTrigger>
            <TabsTrigger
              value="latest"
              className="text-[10px] md:text-xs font-mono font-semibold py-1 rounded-md"
            >
              Latest
            </TabsTrigger>
            <TabsTrigger
              value="ai"
              className="text-[10px] md:text-xs font-mono font-semibold py-1 rounded-md"
            >
              AI Insights
            </TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-y-auto pr-1">
            <TabsContent value="editors-picks" className="mt-0">
              <HeroInsightsList articles={editorPicks} onInsightClick={onInsightClick} />
            </TabsContent>
            <TabsContent value="latest" className="mt-0">
              <HeroInsightsList articles={latest} onInsightClick={onInsightClick} />
            </TabsContent>
            <TabsContent value="ai" className="mt-0">
              <HeroInsightsList articles={aiInsights} onInsightClick={onInsightClick} />
            </TabsContent>
          </div>
        </Tabs>
      </div>

      {/* Mobile: Accordion */}
      <div className="block md:hidden">
        <Accordion type="single" collapsible defaultValue="editors-picks" className="w-full">
          <AccordionItem value="editors-picks" className="border-border/60">
            <AccordionTrigger className="text-xs font-mono font-bold hover:no-underline">
              Editor&apos;s Picks
            </AccordionTrigger>
            <AccordionContent>
              <HeroInsightsList articles={editorPicks} onInsightClick={onInsightClick} />
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="latest" className="border-border/60">
            <AccordionTrigger className="text-xs font-mono font-bold hover:no-underline">
              Latest Articles
            </AccordionTrigger>
            <AccordionContent>
              <HeroInsightsList articles={latest} onInsightClick={onInsightClick} />
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="ai" className="border-none">
            <AccordionTrigger className="text-xs font-mono font-bold hover:no-underline">
              AI Insights
            </AccordionTrigger>
            <AccordionContent>
              <HeroInsightsList articles={aiInsights} onInsightClick={onInsightClick} />
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
    </m.div>
  );
}

HeroInsights.displayName = "HeroInsights";
