"use client";

import React, {
  createContext,
  useState,
  useRef,
  useContext,
  useCallback,
  useEffect,
  ReactNode,
} from "react";
import { usePathname } from "next/navigation";
import { AnimatePresence, m } from "framer-motion";
import { PageTurnTransition } from "@/components/layout/PageTurnTransition";
import { ArticlePeelTransition } from "@/components/layout/ArticlePeelTransition";
import { DepthRevealTransition } from "@/components/layout/DepthRevealTransition";

// ---------------------------------------------------------------------------
// Route ordering – direction-aware navigation
// ---------------------------------------------------------------------------
const ROUTE_ORDER: Record<string, number> = {
  "/": 0,
  "/topics": 1,
  // Future routes slot in naturally:
  // "/bookmarks": 2,
  // "/research": 3,
};

function getRouteIndex(pathname: string): number {
  // Exact match first
  if (ROUTE_ORDER[pathname] !== undefined) return ROUTE_ORDER[pathname];
  // Article pages sit at the highest index
  if (pathname.startsWith("/articles/")) return 100;
  // Unknown routes default to 50 (middle)
  return 50;
}

// ---------------------------------------------------------------------------
// Transition types
// ---------------------------------------------------------------------------
export type TransitionType =
  | "page-turn-forward"
  | "page-turn-backward"
  | "article-open"
  | "article-close"
  | "depth-reveal"
  | "depth-close"
  | "default";

// ---------------------------------------------------------------------------
// Card elevation context — lets article cards signal their position
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
// RouteTransitionProvider
// ---------------------------------------------------------------------------
interface RouteTransitionProviderProps {
  children: ReactNode;
}

export function RouteTransitionProvider({ children }: RouteTransitionProviderProps) {
  return <>{children}</>;
}

// ---------------------------------------------------------------------------
// Transition type determination — uses route ordering
// ---------------------------------------------------------------------------
function determineTransitionType(prevPath: string | null, currentPath: string): TransitionType {
  if (!prevPath) return "default";

  const prevIndex = getRouteIndex(prevPath);
  const currentIndex = getRouteIndex(currentPath);

  const isArticle = (p: string) => p.startsWith("/articles/");
  const isHome = (p: string) => p === "/";
  const isTopics = (p: string) => p === "/topics";
  const isNavRoute = (p: string) => isHome(p) || isTopics(p);

  // Home ↔ Article: paper peel
  if (isHome(prevPath) && isArticle(currentPath)) return "article-open";
  if (isArticle(prevPath) && isHome(currentPath)) return "article-close";

  // Topics ↔ Article: depth reveal
  if (isTopics(prevPath) && isArticle(currentPath)) return "depth-reveal";
  if (isArticle(prevPath) && isTopics(currentPath)) return "depth-close";

  // Navigation between main routes: page turn
  if (isNavRoute(prevPath) && isNavRoute(currentPath)) {
    return currentIndex > prevIndex ? "page-turn-forward" : "page-turn-backward";
  }

  return "default";
}

// ---------------------------------------------------------------------------
// FrozenPage — caches children across route transitions
// ---------------------------------------------------------------------------
interface FrozenPageProps {
  pathname: string;
  transitionType: TransitionType;
  cardRect: DOMRect | null;
  onExitComplete?: () => void;
  children: ReactNode;
}

const FrozenPage = React.forwardRef<HTMLDivElement, FrozenPageProps>(
  ({ pathname, transitionType, cardRect, children }, ref) => {
  const savedChildren = useRef(children);
  const savedPathname = useRef(pathname);

  // Only update cached children when rendering for the matching pathname
  if (pathname === savedPathname.current) {
    savedChildren.current = children;
  }

  // Page turn transitions (Home ↔ Topics and future nav routes)
  if (transitionType === "page-turn-forward" || transitionType === "page-turn-backward") {
    return (
      <PageTurnTransition
        ref={ref}
        pathname={savedPathname.current}
        direction={transitionType === "page-turn-forward" ? "forward" : "backward"}
      >
        {savedChildren.current}
      </PageTurnTransition>
    );
  }

  // Article peel transitions (Home ↔ Article)
  if (transitionType === "article-open" || transitionType === "article-close") {
    return (
      <ArticlePeelTransition
        ref={ref}
        pathname={savedPathname.current}
        direction={transitionType === "article-open" ? "open" : "close"}
        cardRect={cardRect}
      >
        {savedChildren.current}
      </ArticlePeelTransition>
    );
  }

  // Depth reveal transitions (Topics ↔ Article)
  if (transitionType === "depth-reveal" || transitionType === "depth-close") {
    return (
      <DepthRevealTransition
        ref={ref}
        pathname={savedPathname.current}
        direction={transitionType === "depth-reveal" ? "open" : "close"}
      >
        {savedChildren.current}
      </DepthRevealTransition>
    );
  }

  // Default transition
  return (
    <DefaultTransition ref={ref} pathname={savedPathname.current}>
      {savedChildren.current}
    </DefaultTransition>
  );
});

// ---------------------------------------------------------------------------
// Default fallback transition — simple crossfade
// ---------------------------------------------------------------------------
const DefaultTransition = React.forwardRef<HTMLDivElement, { pathname: string; children: ReactNode }>(
  ({ pathname, children }, ref) => {
    return (
      <m.div
        ref={ref}
        key={pathname}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15, ease: "easeInOut" }}
        className="w-full min-h-screen flex flex-col"
      >
        {children}
      </m.div>
    );
  }
);
