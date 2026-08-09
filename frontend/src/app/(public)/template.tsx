"use client";

import React, { useRef, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import {
  useArticleTransition,
  determineTransitionType,
} from "@/components/layout/RouteTransitionProvider";
import { ArticlePeelTransition } from "@/components/layout/ArticlePeelTransition";
import { PageTurnTransition } from "@/components/layout/PageTurnTransition";
import { DepthRevealTransition } from "@/components/layout/DepthRevealTransition";
import { PageTransition } from "@/components/layout/PageTransition";

export default function PublicTemplate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const prevPathRef = useRef<string | null>(null);
  const { cardRect, cardImageSrc, cardTitle } = useArticleTransition();
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    prevPathRef.current = pathname;
  }, [pathname]);

  if (!isMounted) {
    return <>{children}</>;
  }

  const prevPath = prevPathRef.current;
  const transitionType = determineTransitionType(prevPath, pathname);

  if (transitionType === "article-open" || transitionType === "article-close") {
    return (
      <ArticlePeelTransition
        pathname={pathname}
        direction={transitionType === "article-open" ? "open" : "close"}
        cardRect={cardRect}
        cardImageSrc={cardImageSrc}
        cardTitle={cardTitle}
      >
        {children}
      </ArticlePeelTransition>
    );
  }

  if (transitionType === "page-turn-forward" || transitionType === "page-turn-backward") {
    return (
      <PageTurnTransition
        pathname={pathname}
        direction={transitionType === "page-turn-forward" ? "forward" : "backward"}
      >
        {children}
      </PageTurnTransition>
    );
  }

  const isTopicsOrArticle = false;

  if (isTopicsOrArticle) {
    const isOpening = pathname.startsWith("/articles/");
    return (
      <DepthRevealTransition
        pathname={pathname}
        direction={isOpening ? "open" : "close"}
      >
        {children}
      </DepthRevealTransition>
    );
  }

  return <PageTransition>{children}</PageTransition>;
}
