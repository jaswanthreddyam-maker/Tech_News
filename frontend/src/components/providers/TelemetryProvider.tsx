"use client";

import React, { createContext, useContext, useCallback } from "react";
import { useAnalytics } from "./AnalyticsProvider";
import { BUILD_CONFIG } from "@/config/build";

interface TelemetryContextType {
  logError: (level: string, message: string, context?: any) => void;
  logPerformance: (metric: string, value: number, context?: any) => void;
}

const TelemetryContext = createContext<TelemetryContextType | undefined>(undefined);

export function TelemetryProvider({ children }: { children: React.ReactNode }) {
  const { track } = useAnalytics();

  const logError = useCallback((level: string, message: string, context?: any) => {
    // Forward to AnalyticsProvider
    track("System Error", { level, message, ...context, buildVersion: BUILD_CONFIG.version });
  }, [track]);

  const logPerformance = useCallback((metric: string, value: number, context?: any) => {
    // Forward to AnalyticsProvider
    track("Performance Metric", { metric, value, ...context, buildVersion: BUILD_CONFIG.version });
  }, [track]);

  return (
    <TelemetryContext.Provider value={{ logError, logPerformance }}>
      {children}
    </TelemetryContext.Provider>
  );
}

export function useTelemetry() {
  const context = useContext(TelemetryContext);
  if (context === undefined) {
    throw new Error("useTelemetry must be used within a TelemetryProvider");
  }
  return context;
}
