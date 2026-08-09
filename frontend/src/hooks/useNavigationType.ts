"use client";

import { useEffect, useState } from "react";

/**
 * useNavigationType
 *
 * Determines whether the current page load is a "cold load"
 * (direct URL, refresh, new tab) or a "client navigation"
 * (Next.js router.push from within the app).
 *
 * Uses the Navigation API (Chrome 102+) with a PerformanceNavigation fallback.
 * Never uses sessionStorage — avoids breakage on new tabs, refresh, tab restore.
 *
 * Usage:
 *   const { isColdLoad } = useNavigationType();
 *   if (isColdLoad) { // play full entrance animation }
 *   else { // page transition only }
 */
export function useNavigationType() {
  const [isColdLoad, setIsColdLoad] = useState(true);

  useEffect(() => {
    let cold = true;

    // Navigation API (Chrome 102+, Edge 102+)
    if (typeof window !== "undefined" && "navigation" in window) {
      const nav = (window as any).navigation;
      // navigationType: "push" | "replace" | "traverse" | "reload"
      // "push" = client navigation, "reload"/"traverse" = cold-ish
      if (nav?.currentEntry?.navigationType === "push" ||
          nav?.currentEntry?.navigationType === "replace") {
        cold = false;
      }
    } else if (typeof window !== "undefined" && window.performance) {
      // PerformanceNavigationTiming (widely supported fallback)
      const entries = window.performance.getEntriesByType("navigation") as PerformanceNavigationTiming[];
      if (entries.length > 0) {
        const type = entries[0].type;
        // "navigate" = cold load or direct URL
        // "back_forward" = browser back/forward button
        // "reload" = refresh
        // For our purposes: only "navigate" to an article from homepage counts as client nav
        // We detect client nav by checking if referrer is same-origin
        if (type === "navigate" && document.referrer) {
          try {
            const ref = new URL(document.referrer);
            if (ref.origin === window.location.origin) {
              cold = false;
            }
          } catch {
            // invalid referrer — treat as cold
          }
        }
      }
    }

    setIsColdLoad(cold);
  }, []);

  return { isColdLoad };
}
