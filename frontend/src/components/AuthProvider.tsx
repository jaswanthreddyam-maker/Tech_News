/* eslint-disable no-console */
"use client";

import { useEffect, useCallback } from "react";
import { useAppStore } from "../store/useStore";
import { sessionManager } from "@/lib/session/sessionManager";

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const { loginUser, logoutUser, setRestoringSession, setAuthRefreshSuppressUntil } = useAppStore();

  const initializeSession = useCallback(
    async (force = false) => {
      // 1. Optimistic hydration on mount: restore cached user & token
      if (typeof window !== "undefined") {
        const cachedUser = sessionManager.getCachedUser();
        const activeToken = sessionManager.getAccessToken();

        if (cachedUser && activeToken && !useAppStore.getState().user) {
          loginUser(cachedUser, activeToken);
        }

        if (!sessionManager.isAuthenticated() && !localStorage.getItem("has_session")) {
          setRestoringSession(false);
          return;
        }
      }

      // 2. Check refresh suppression guard
      if (!force) {
        const suppressUntil = useAppStore.getState().authRefreshSuppressUntil;
        if (suppressUntil && suppressUntil > Date.now()) {
          setRestoringSession(false);
          return;
        }
      }

      // 3. If local access token is still valid and we have a cached user, skip server refresh
      if (sessionManager.isAuthenticated() && useAppStore.getState().user) {
        setRestoringSession(false);
        return;
      }

      // 4. Perform background silent token refresh via cookie-based refresh token
      try {
        const data = await sessionManager.refresh();
        if (data && data.user && data.access_token) {
          setAuthRefreshSuppressUntil(null);
          loginUser(data.user, data.access_token);
        } else if (!sessionManager.isAuthenticated()) {
          logoutUser();
        }
      } catch {
        if (!sessionManager.isAuthenticated()) {
          logoutUser();
        }
      } finally {
        setRestoringSession(false);
      }
    },
    [loginUser, logoutUser, setRestoringSession, setAuthRefreshSuppressUntil]
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
