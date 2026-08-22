"use client";

import { useEffect, useCallback } from "react";
import { useAppStore } from "@/store/useStore";
import { sessionManager } from "@/lib/session/sessionManager";

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const { loginUser, logoutUser, setRestoringSession, setAuthRefreshSuppressUntil } = useAppStore();

  const initializeSession = useCallback(
    async (force = false) => {
      if (!force) {
        const suppressUntil = useAppStore.getState().authRefreshSuppressUntil;
        if (suppressUntil && suppressUntil > Date.now()) {
          setRestoringSession(false);
          return;
        }
      }

      try {
        const data = await sessionManager.refresh();
        if (data && data.user && data.access_token) {
          setAuthRefreshSuppressUntil(null);
          loginUser(data.user, data.access_token);
        } else {
          setAuthRefreshSuppressUntil(Date.now() + 300000);
        }
      } catch (e: any) {
        setAuthRefreshSuppressUntil(Date.now() + 300000);
      } finally {
        setRestoringSession(false);
      }
    },
    [loginUser, setRestoringSession, setAuthRefreshSuppressUntil]
  );

  useEffect(() => {
    initializeSession();
  }, [initializeSession]);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === "has_session" || e.key === "session_event") {
        if (e.newValue === "true" || e.newValue?.startsWith("login")) {
          setAuthRefreshSuppressUntil(null);
          initializeSession(true);
        } else if (e.newValue === null || e.newValue === "false" || e.newValue?.startsWith("logout")) {
          logoutUser();
        }
      }
    };

    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, [initializeSession, logoutUser, setAuthRefreshSuppressUntil]);

  return <>{children}</>;
}
