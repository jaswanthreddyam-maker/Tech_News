"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { Clock, Calendar } from "lucide-react";
import { m, useReducedMotion } from "framer-motion";
import { useNavigationType } from "@/hooks/useNavigationType";
import { DURATION, EASING, REVEAL_DELAYS } from "@/design-system/motion/tokens";

import { getPresentationConfig } from "@/domains/article/presentation";
import { CardHeader } from "@/components/common/card/primitives";

interface ArticleHeaderProps {
  title: string;
  category: string;
  publishedAt: string;
  readingTimeMin: number;
  documentType?: string;
  isMultiTopic?: boolean;
}

export function ArticleHeader({ title, category, publishedAt, readingTimeMin, documentType, isMultiTopic }: ArticleHeaderProps) {
  const shouldReduceMotion = useReducedMotion();
  const { isColdLoad } = useNavigationType();

  const presentation = getPresentationConfig(documentType, isMultiTopic);

  // Headline: blur + translate (no scale — text never scales)
  // Only plays on cold load; client navigation skips the stagger
  const titleVariants = {
    hidden: shouldReduceMotion
      ? { opacity: 0 }
      : { opacity: 0, y: 20, filter: "blur(8px)" },
    visible: {
      opacity: 1,
      y: 0,
      filter: "blur(0px)",
      transition: {
        duration: shouldReduceMotion ? 0.15 : DURATION.slow,
        ease: (shouldReduceMotion ? "linear" : EASING.standard) as any,
        // Delay only on cold load — aligns with the progressive reveal order
        delay: isColdLoad && !shouldReduceMotion ? REVEAL_DELAYS.meta : 0,
      },
    },
  };

  const metaVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        duration: DURATION.fast,
        delay: isColdLoad && !shouldReduceMotion ? REVEAL_DELAYS.meta * 0.5 : 0,
      },
    },
  };

  return (
    <header className="space-y-6">
      {/* Meta tags */}
      <m.div
        initial={isColdLoad ? "hidden" : false}
        animate="visible"
        variants={metaVariants}
        className="flex flex-wrap items-center gap-3 text-xs font-mono uppercase tracking-wider text-muted-foreground"
      >
        <CardHeader badge={presentation.badge} category={category} />

        <div className="flex items-center gap-1.5">
          <Calendar className="w-3.5 h-3.5" />
          <time dateTime={publishedAt} suppressHydrationWarning>
            {new Date(publishedAt).toLocaleDateString("en-US", {
              year: "numeric",
              month: "long",
              day: "numeric",
              timeZone: "UTC",
            })}
          </time>
        </div>

        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5" />
          <span>{readingTimeMin} Min Read</span>
        </div>
      </m.div>

      {/* Title — blur+y entrance, no scale */}
      <m.h1
        initial={isColdLoad ? "hidden" : false}
        animate="visible"
        variants={titleVariants}
        className="text-3xl md:text-5xl font-serif font-bold text-foreground leading-tight tracking-tight"
      >
        {title}
      </m.h1>
    </header>
  );
}
