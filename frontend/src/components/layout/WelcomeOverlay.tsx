"use client";

import { useEffect, useState } from "react";
import WelcomeOverlayClient from "./WelcomeOverlayClient";

export function WelcomeOverlay({ children }: { children: React.ReactNode }) {
  const [isMounted, setIsMounted] = useState(false);
  const [hasPlayed, setHasPlayed] = useState<boolean | null>(null);

  useEffect(() => {
    setIsMounted(true);
    const played = sessionStorage.getItem("welcome-played") === "1";
    setHasPlayed(played);
  }, []);

  // During SSR (isMounted=false) or before client-side sessionStorage check is complete (hasPlayed=null),
  // we default to showing the overlay to guarantee that the dashboard is covered on first paint.
  const showOverlay = !isMounted || hasPlayed === null || hasPlayed === false;

  return (
    <>
      {showOverlay && (
        <WelcomeOverlayClient
          isMounted={isMounted}
          hasPlayed={hasPlayed}
          onComplete={() => {
            sessionStorage.setItem("welcome-played", "1");
            setHasPlayed(true);
          }}
        />
      )}
      {children}
    </>
  );
}
