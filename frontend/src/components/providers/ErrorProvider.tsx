"use client";

import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import { useAppStore } from "@/store/useStore";
import { BUILD_CONFIG } from "@/config/build";
import { ErrorAdapter, ErrorContext } from "@/lib/error/types";
import { ConsoleAdapter } from "@/lib/error/adapters/ConsoleAdapter";
// import { SentryAdapter } from "@/lib/error/adapters/SentryAdapter";
import { CustomBackendAdapter } from "@/lib/error/adapters/CustomBackendAdapter";
import { useTelemetry } from "./TelemetryProvider";

interface ErrorProviderContextType {
  captureException: (error: Error, additionalContext?: Partial<ErrorContext>) => void;
  captureMessage: (message: string, additionalContext?: Partial<ErrorContext>) => void;
  captureWarning: (message: string, additionalContext?: Partial<ErrorContext>) => void;
}

const ErrorContextContext = createContext<ErrorProviderContextType | undefined>(undefined);

export function ErrorProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user } = useAppStore();
  const { logError } = useTelemetry();

  const [adapters] = useState<ErrorAdapter[]>(() => {
    const list: ErrorAdapter[] = [new ConsoleAdapter(), new CustomBackendAdapter()];
    // Normally you'd conditionally add Sentry based on env variables
    // list.push(new SentryAdapter());
    return list;
  });

  const [sessionId] = useState(() => 
    typeof window !== "undefined" ? crypto.randomUUID() : null
  );

  const [anonymousId, setAnonymousId] = useState<string | null>(null);

  useEffect(() => {
    let id = localStorage.getItem("tnt_anonymous_id");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("tnt_anonymous_id", id);
    }
    setAnonymousId(id);
  }, []);

  const baseContext: Partial<ErrorContext> = useMemo(() => {
    let browser = "unknown";
    let viewport = "unknown";
    if (typeof window !== "undefined") {
      browser = navigator.userAgent;
      viewport = `${window.innerWidth}x${window.innerHeight}`;
    }

    return {
      route: pathname,
      userId: user?.id?.toString() || null,
      anonymousId,
      buildVersion: BUILD_CONFIG.version,
      // We could extract active feature flags from a hook if needed
      featureFlags: [], 
      browser,
      viewport,
      sessionId
    };
  }, [pathname, user, anonymousId, sessionId]);

  const captureException = (error: Error, additionalContext?: Partial<ErrorContext>) => {
    const ctx = { ...baseContext, ...additionalContext };
    adapters.forEach(adapter => adapter.captureException(error, ctx));
    logError("error", error.message, ctx);
  };

  const captureMessage = (message: string, additionalContext?: Partial<ErrorContext>) => {
    const ctx = { ...baseContext, ...additionalContext };
    adapters.forEach(adapter => adapter.captureMessage(message, ctx));
    logError("info", message, ctx);
  };

  const captureWarning = (message: string, additionalContext?: Partial<ErrorContext>) => {
    const ctx = { ...baseContext, ...additionalContext };
    adapters.forEach(adapter => adapter.captureWarning(message, ctx));
    logError("warning", message, ctx);
  };

  return (
    <ErrorContextContext.Provider value={{ captureException, captureMessage, captureWarning }}>
      {children}
    </ErrorContextContext.Provider>
  );
}

export function useErrorTracking() {
  const context = useContext(ErrorContextContext);
  if (context === undefined) {
    throw new Error("useErrorTracking must be used within an ErrorProvider");
  }
  return context;
}
