/* eslint-disable no-console */
"use client";

import { useEffect } from "react";
import { useAppStore } from "../store/useStore";

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const { loginUser, setRestoringSession, setAuthRefreshSuppressUntil } = useAppStore();

  useEffect(() => {
    // Gate 1: Only attempt session restore if user previously logged in
    const hadSession = typeof window !== "undefined" && localStorage.getItem("has_session") === "true";
    if (!hadSession) {
      setRestoringSession(false);
      return;
    }

    // Gate 2: Skip if refresh is currently suppressed (e.g. after a recent 401)
    const suppressUntil = useAppStore.getState().authRefreshSuppressUntil;
    if (suppressUntil && suppressUntil > Date.now()) {
      setRestoringSession(false);
      return;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      controller.abort();
      setRestoringSession(false);
      setAuthRefreshSuppressUntil(Date.now() + 300000);
    }, 3000);

    const initializeSession = async () => {
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
    };

    initializeSession();
  }, [loginUser, setRestoringSession, setAuthRefreshSuppressUntil]);

  return <>{children}</>;
}
