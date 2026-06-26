"use client";

import React, { createContext, useContext, useCallback } from "react";
import { useReportWebVitals } from "next/web-vitals";
import { useTelemetry } from "./TelemetryProvider";

interface PerformanceContextType {
  trackLatency: (metric: string, durationMs: number, metadata?: any) => void;
}

const PerformanceContext = createContext<PerformanceContextType | undefined>(undefined);

export function PerformanceProvider({ children }: { children: React.ReactNode }) {
  const { logPerformance } = useTelemetry();

  useReportWebVitals((metric) => {
    // Forward Core Web Vitals (LCP, CLS, INP, FCP, TTFB)
    logPerformance(`Web Vital: ${metric.name}`, metric.value, { 
      id: metric.id, 
      label: metric.label 
    });
  });

  const trackLatency = useCallback((metric: string, durationMs: number, metadata?: any) => {
    logPerformance(`Latency: ${metric}`, durationMs, metadata);
  }, [logPerformance]);

  return (
    <PerformanceContext.Provider value={{ trackLatency }}>
      {children}
    </PerformanceContext.Provider>
  );
}

export function usePerformanceTracking() {
  const context = useContext(PerformanceContext);
  if (context === undefined) {
    throw new Error("usePerformanceTracking must be used within a PerformanceProvider");
  }
  return context;
}
