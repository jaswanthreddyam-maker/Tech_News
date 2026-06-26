"use client";

import { useEffect } from "react";
import { useAppStore } from "@/store/useStore";
import { sessionManager } from "@/lib/session/sessionManager";

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const { loginUser, setRestoringSession, setAuthRefreshSuppressUntil, authRefreshSuppressUntil } = useAppStore();

  useEffect(() => {
    if (authRefreshSuppressUntil && authRefreshSuppressUntil > Date.now()) {
      setRestoringSession(false);
      return;
    }

    const initializeSession = async () => {
      try {
        const data = await sessionManager.refresh();
        if (data && data.user && data.access_token) {
          loginUser(data.user, data.access_token);
        } else {
          setAuthRefreshSuppressUntil(Date.now() + 300000);
        }
      } catch (e: any) {
        // eslint-disable-next-line no-console

        setAuthRefreshSuppressUntil(Date.now() + 300000);
      } finally {
        setRestoringSession(false);
      }
    };

    initializeSession();
  }, [loginUser, setRestoringSession, setAuthRefreshSuppressUntil, authRefreshSuppressUntil]);

  return <>{children}</>;
}
