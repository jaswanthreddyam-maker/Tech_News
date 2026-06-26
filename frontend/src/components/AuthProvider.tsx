/* eslint-disable no-console */
"use client";

import { useEffect } from "react";
import { useAppStore } from "../store/useStore";

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const { loginUser, setRestoringSession, setAuthRefreshSuppressUntil } = useAppStore();

  useEffect(() => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {

      controller.abort();
      setRestoringSession(false);
      
      // Suppress subsequent refresh attempts for 5 minutes
      const suppressUntil = Date.now() + 300000;
      setAuthRefreshSuppressUntil(suppressUntil);
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
            const suppressUntil = Date.now() + 300000;
            setAuthRefreshSuppressUntil(suppressUntil);
          }
        }
      } catch (e: any) {
        if (e.name === "AbortError") {

        } else {

        }
        const suppressUntil = Date.now() + 300000;
        setAuthRefreshSuppressUntil(suppressUntil);
      } finally {
        clearTimeout(timeoutId);
        setRestoringSession(false);
      }
    };

    initializeSession();
  }, [loginUser, setRestoringSession, setAuthRefreshSuppressUntil]);

  return <>{children}</>;
}
