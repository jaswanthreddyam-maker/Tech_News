"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { Clock, Calendar } from "lucide-react";
import { m, useReducedMotion } from "framer-motion";

interface ArticleHeaderProps {
  title: string;
  category: string;
  publishedAt: string;
  readingTimeMin: number;
}

export function ArticleHeader({ title, category, publishedAt, readingTimeMin }: ArticleHeaderProps) {
  const shouldReduceMotion = useReducedMotion();

  const titleVariants = {
    hidden: shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 15 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: shouldReduceMotion ? 0.15 : 0.6,
        ease: (shouldReduceMotion ? "linear" : [0.22, 1, 0.36, 1]) as any,
      },
    },
  };

  return (
    <header className="space-y-6">
      {/* Meta tags */}
      <div className="flex flex-wrap items-center gap-4 text-xs font-mono uppercase tracking-wider text-muted-foreground">
        <Badge variant="outline" className="text-primary border-primary/30 bg-primary/5 rounded-full px-3 py-1">
          {category}
        </Badge>
        
        <div className="flex items-center gap-1.5">
          <Calendar className="w-3.5 h-3.5" />
          <time dateTime={publishedAt} suppressHydrationWarning>
            {new Date(publishedAt).toLocaleDateString("en-US", {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
              timeZone: 'UTC'
            })}
          </time>
        </div>

        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5" />
          <span>{readingTimeMin} Min Read</span>
        </div>
      </div>

      {/* Title */}
      <m.h1
        initial={false}
        animate="visible"
        variants={titleVariants}
        className="text-3xl md:text-5xl font-serif font-bold text-foreground leading-tight tracking-tight"
      >
        {title}
      </m.h1>
    </header>
  );
}
