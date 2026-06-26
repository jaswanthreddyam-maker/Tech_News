"use client";

import React, { createContext, useContext, useEffect, useCallback, useRef } from "react";
import { AnalyticsEvent, AnalyticsPayload } from "@/lib/analytics/events";
import { usePathname } from "next/navigation";
import { useAppStore } from "@/store/useStore";

interface AnalyticsContextType {
  track: (event: AnalyticsEvent, payload?: AnalyticsPayload) => void;
}

const AnalyticsContext = createContext<AnalyticsContextType | undefined>(undefined);

export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user } = useAppStore();
  const userId = user?.id;
  const lastPathname = useRef<string | null>(null);

  const track = useCallback((event: AnalyticsEvent, payload?: AnalyticsPayload) => {
    // In production this would push to Mixpanel, Segment, PostHog, etc.
    const enrichedPayload = {
      ...payload,
      userId: userId || "anonymous",
      timestamp: new Date().toISOString(),
      url: window.location.href,
    };
    
    // eslint-disable-next-line no-console

  }, [userId]);

  // Automatic Page View tracking
  useEffect(() => {
    if (pathname && pathname !== lastPathname.current) {
      lastPathname.current = pathname;
      track("Page Viewed", { path: pathname });
    }
  }, [pathname, track]);

  return (
    <AnalyticsContext.Provider value={{ track }}>
      {children}
    </AnalyticsContext.Provider>
  );
}

export function useAnalytics() {
  const context = useContext(AnalyticsContext);
  if (!context) {
    // Fallback if used outside of provider
    return {
      track: (event: AnalyticsEvent, payload?: AnalyticsPayload) => {
        // eslint-disable-next-line no-console

      }
    };
  }
  return context;
}
