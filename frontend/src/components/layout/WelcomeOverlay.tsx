"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import WelcomeOverlayClient from "./WelcomeOverlayClient";

interface WelcomeOverlayProps {
  children: React.ReactNode;
}

export function WelcomeOverlay({ children }: WelcomeOverlayProps) {
  // null = loading, false = show overlay (desktop only), true = already played / mobile
  const [hasPlayed, setHasPlayed] = useState<boolean | null>(null);
  const completedRef = useRef(false);

  useEffect(() => {
    try {
      // Mobile viewports (< 768px) bypass welcome overlay completely
      const isMobile = window.matchMedia("(max-width: 767px)").matches;
      if (isMobile) {
        setHasPlayed(true);
        return;
      }
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
      {children}
    </>
  );
}