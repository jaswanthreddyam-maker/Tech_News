/* eslint-disable no-console */
"use client";

import { useEffect, useCallback } from "react";
import { useAppStore } from "../store/useStore";

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const { loginUser, logoutUser, setRestoringSession, setAuthRefreshSuppressUntil } = useAppStore();

  const initializeSession = useCallback(
    async (force = false) => {
      // Gate 1: Only attempt session restore if user previously logged in
      const hadSession = typeof window !== "undefined" && localStorage.getItem("has_session") === "true";
      if (!hadSession) {
        setRestoringSession(false);
        return;
      }

      // Gate 2: Skip if refresh is currently suppressed (unless forced by cross-tab sync event)
      if (!force) {
        const suppressUntil = useAppStore.getState().authRefreshSuppressUntil;
        if (suppressUntil && suppressUntil > Date.now()) {
          setRestoringSession(false);
          return;
        }
      }

      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        controller.abort();
        setRestoringSession(false);
        setAuthRefreshSuppressUntil(Date.now() + 300000);
      }, 4000);

      try {
        const apiBase = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
        const response = await fetch(`${apiBase}/auth/refresh`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          signal: controller.signal,
        });

        if (response.ok) {
          const payload = await response.json();
          const data = payload.data || payload;
          if (data.access_token && data.user) {
            setAuthRefreshSuppressUntil(null);
            loginUser(data.user, data.access_token);
          }
        } else {
          if (response.status === 401 || response.status === 403) {
            // Refresh token is invalid/expired — clear session marker and suppress
            localStorage.removeItem("has_session");
            setAuthRefreshSuppressUntil(Date.now() + 300000);
          }
        }
      } catch (e: any) {
        if (e.name !== "AbortError") {
          setAuthRefreshSuppressUntil(Date.now() + 300000);
        }
      } finally {
        clearTimeout(timeoutId);
        setRestoringSession(false);
      }
    },
    [loginUser, setRestoringSession, setAuthRefreshSuppressUntil]
  );

  useEffect(() => {
    initializeSession();
  }, [initializeSession]);

  // Listen for cross-tab authentication events (sign-up / login / logout in other tabs)
  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === "has_session" || e.key === "session_event") {
        if (e.newValue === "true" || e.newValue?.startsWith("login")) {
          // User signed up or logged in in another tab -> sync session in this tab immediately
          setAuthRefreshSuppressUntil(null);
          initializeSession(true);
        } else if (e.newValue === null || e.newValue === "false" || e.newValue?.startsWith("logout")) {
          // User logged out in another tab -> log out this tab
          logoutUser();
        }
      }
    };

    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, [initializeSession, logoutUser, setAuthRefreshSuppressUntil]);

  return <>{children}</>;
}
