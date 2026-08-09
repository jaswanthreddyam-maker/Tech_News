"use client";

import React, {
  createContext,
  useState,
  useContext,
  useCallback,
  ReactNode,
} from "react";

// ---------------------------------------------------------------------------
// Article transition context — card rect captured at click time
// ---------------------------------------------------------------------------

interface ArticleTransitionData {
  cardRect: DOMRect | null;
  cardImageSrc: string | null;
  cardTitle: string | null;
}

interface ArticleTransitionContextValue extends ArticleTransitionData {
  setTransitionData: (data: Partial<ArticleTransitionData>) => void;
  clearTransitionData: () => void;
}

const ArticleTransitionContext = createContext<ArticleTransitionContextValue>({
  cardRect: null,
  cardImageSrc: null,
  cardTitle: null,
  setTransitionData: () => {},
  clearTransitionData: () => {},
});

/**
 * useArticleTransition
 *
 * Hook for article cards to signal their position before navigating.
 * Usage:
 *   const { setTransitionData } = useArticleTransition();
 *   onClick={(e) => setTransitionData({ cardRect: e.currentTarget.getBoundingClientRect(), ... })}
 */
export function useArticleTransition() {
  return useContext(ArticleTransitionContext);
}

// ---------------------------------------------------------------------------
// CardElevation context — kept for backward compat
// ---------------------------------------------------------------------------
interface CardElevationState {
  cardRect: DOMRect | null;
  setCardRect: (rect: DOMRect | null) => void;
}

const CardElevationContext = createContext<CardElevationState>({
  cardRect: null,
  setCardRect: () => {},
});

export function useCardElevation() {
  return useContext(CardElevationContext);
}

// ---------------------------------------------------------------------------
// Route ordering
// ---------------------------------------------------------------------------
const ROUTE_ORDER: Record<string, number> = {
  "/": 0,
  "/topics": 1,
};

function getRouteIndex(pathname: string): number {
  if (ROUTE_ORDER[pathname] !== undefined) return ROUTE_ORDER[pathname];
  if (pathname.startsWith("/articles/")) return 100;
  return 50;
}

// ---------------------------------------------------------------------------
// Transition types
// ---------------------------------------------------------------------------
export type TransitionType =
  | "article-open"
  | "article-close"
  | "page-turn-forward"
  | "page-turn-backward"
  | "default";

export function determineTransitionType(
  prevPath: string | null,
  currentPath: string
): TransitionType {
  if (!prevPath) return "default";

  const prevIndex = getRouteIndex(prevPath);
  const currentIndex = getRouteIndex(currentPath);

  const isArticle = (p: string) => p.startsWith("/articles/");
  const isHome = (p: string) => p === "/";
  const isTopics = (p: string) => p === "/topics";
  const isNavRoute = (p: string) => isHome(p) || isTopics(p);

  if (isNavRoute(prevPath) && isArticle(currentPath)) return "article-open";
  if (isArticle(prevPath) && isNavRoute(currentPath)) return "article-close";

  if (isNavRoute(prevPath) && isNavRoute(currentPath)) {
    return currentIndex > prevIndex ? "page-turn-forward" : "page-turn-backward";
  }

  return "default";
}

// ---------------------------------------------------------------------------
// RouteTransitionProvider
// ---------------------------------------------------------------------------
interface RouteTransitionProviderProps {
  children: ReactNode;
}

export function RouteTransitionProvider({ children }: RouteTransitionProviderProps) {
  const [transitionData, setTransitionDataState] = useState<ArticleTransitionData>({
    cardRect: null,
    cardImageSrc: null,
    cardTitle: null,
  });

  // Also expose legacy cardRect via CardElevationContext
  const [cardRect, setCardRect] = useState<DOMRect | null>(null);

  const setTransitionData = useCallback((data: Partial<ArticleTransitionData>) => {
    setTransitionDataState((prev) => ({ ...prev, ...data }));
    if (data.cardRect !== undefined) setCardRect(data.cardRect);
  }, []);

  const clearTransitionData = useCallback(() => {
    setTransitionDataState({ cardRect: null, cardImageSrc: null, cardTitle: null });
    setCardRect(null);
  }, []);

  return (
    <ArticleTransitionContext.Provider
      value={{ ...transitionData, setTransitionData, clearTransitionData }}
    >
      <CardElevationContext.Provider value={{ cardRect, setCardRect }}>
        {children}
      </CardElevationContext.Provider>
    </ArticleTransitionContext.Provider>
  );
}
