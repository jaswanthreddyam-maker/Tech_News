"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";

const STORAGE_KEY = "tnt:homepage:scrollY";

/**
 * useScrollRestoration
 *
 * Saves homepage scroll position when navigating away,
 * and restores it when returning via back navigation.
 *
 * Usage (homepage only):
 *   useScrollRestoration();
 *
 * How it works:
 * - On unmount: saves window.scrollY to sessionStorage
 * - On mount: reads saved scroll and restores it instantly
 * - Only active on the homepage path "/"
 */
export function useScrollRestoration() {
  const pathname = usePathname();
  const isHomepage = pathname === "/";

  useEffect(() => {
    if (!isHomepage) return;

    // Restore scroll position instantly on homepage mount
    const saved = sessionStorage.getItem(STORAGE_KEY);
    if (saved) {
      const y = parseInt(saved, 10);
      if (!isNaN(y) && y > 0) {
        // Use instant scroll — no smooth animation during restoration
        requestAnimationFrame(() => {
          window.scrollTo({ top: y, behavior: "instant" as ScrollBehavior });
        });
      }
      // Clear after restore so fresh visits start at top
      sessionStorage.removeItem(STORAGE_KEY);
    }

    // Save scroll position on page hide (navigating away)
    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        sessionStorage.setItem(STORAGE_KEY, String(Math.round(window.scrollY)));
      }
    };

    // Also save on pagehide (more reliable for back/forward)
    const handlePageHide = () => {
      sessionStorage.setItem(STORAGE_KEY, String(Math.round(window.scrollY)));
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("pagehide", handlePageHide);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("pagehide", handlePageHide);
      // Save on component unmount (client-side navigation away)
      sessionStorage.setItem(STORAGE_KEY, String(Math.round(window.scrollY)));
    };
  }, [isHomepage]);
}
