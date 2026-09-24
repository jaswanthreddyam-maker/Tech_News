"use client";

import React, { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { useArticleTransition } from "@/components/layout/RouteTransitionProvider";
import { ArticlePeelTransition } from "@/components/layout/ArticlePeelTransition";
import { PageTurnTransition } from "@/components/layout/PageTurnTransition";
import { PageTransition } from "@/components/layout/PageTransition";

export default function PublicTemplate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { cardRect, cardImageSrc, cardTitle, transitionType } = useArticleTransition();
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) {
    return <>{children}</>;
  }

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

  return <PageTransition>{children}</PageTransition>;
}

