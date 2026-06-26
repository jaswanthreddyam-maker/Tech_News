"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { sessionManager } from "@/lib/session/sessionManager";
import { useAppStore } from "@/store/useStore";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, isRestoringSession } = useAppStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted && !isRestoringSession) {
      if (!user && !sessionManager.isAuthenticated()) {
        router.replace("/login");
      }
    }
  }, [mounted, isRestoringSession, user, router]);

  // Prevent flash of content while checking session
  if (!mounted || isRestoringSession) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="w-6 h-6 border border-white/20 border-t-white animate-spin rounded-full" />
      </div>
    );
  }

  // Double check
  if (!user && !sessionManager.isAuthenticated()) {
    return null;
  }

  return <>{children}</>;
}
