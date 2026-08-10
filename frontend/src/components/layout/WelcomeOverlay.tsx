"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import WelcomeOverlayClient from "./WelcomeOverlayClient";

interface WelcomeOverlayProps {
  children: React.ReactNode;
}

export function WelcomeOverlay({ children }: WelcomeOverlayProps) {
  // null = loading, false = show overlay, true = already played
  const [hasPlayed, setHasPlayed] = useState<boolean | null>(null);
  const completedRef = useRef(false);

  useEffect(() => {
    try {
      setHasPlayed(sessionStorage.getItem("welcome-played") === "1");
    } catch {
      setHasPlayed(false);
    }
  }, []);

  const handleComplete = useCallback(() => {
    if (completedRef.current) return;
    completedRef.current = true;
    try {
      sessionStorage.setItem("welcome-played", "1");
    } catch {}
    if (typeof document !== "undefined") {
      document.body.style.overflow = "";
    }
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("welcome-overlay-complete"));
    }
    setHasPlayed(true);
  }, []);

  return (
    <>
      {hasPlayed !== true && (
        <WelcomeOverlayClient
          isMounted={hasPlayed !== null}
          hasPlayed={hasPlayed}
          onComplete={handleComplete}
        />
      )}
      {hasPlayed === true && children}
    </>
  );
}