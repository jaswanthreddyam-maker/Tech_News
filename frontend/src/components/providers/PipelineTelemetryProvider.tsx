"use client";

import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { 
  TelemetryClient, 
  TelemetrySnapshotV3, 
  ConnectionState, 
  TelemetryClientCallbacks 
} from "../../services/telemetryClient";

interface PipelineTelemetryContextType {
  snapshot: TelemetrySnapshotV3 | null;
  connectionState: ConnectionState | "stale";
  error: string | null;
  lastUpdated: number | null; // timestamp in ms
  reconnect: () => void;
}

const PipelineTelemetryContext = createContext<PipelineTelemetryContextType | undefined>(undefined);

export const PipelineTelemetryProvider = ({ children }: { children: React.ReactNode }) => {
  const [snapshot, setSnapshot] = useState<TelemetrySnapshotV3 | null>(null);
  const [connectionState, setConnectionState] = useState<ConnectionState | "stale">("loading");
  const [error, setError] = useState<string | null>(null);

  // Initialize TelemetryClient with environment configurations
  const client = useMemo(() => {
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "";
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
    
    // Resolve REST and SSE URLs
    let restUrl = apiBaseUrl ? `${apiBaseUrl}/api/v1/telemetry` : `${apiBase}/telemetry`;
    let sseUrl = apiBaseUrl ? `${apiBaseUrl}/api/v1/telemetry/sse` : `${apiBase}/telemetry/sse`;

    if (typeof window !== "undefined") {
      if (!apiBaseUrl) {
        if (restUrl.startsWith("/")) {
          restUrl = `${window.location.protocol}//${window.location.host}${restUrl}`;
        }
        if (sseUrl.startsWith("/")) {
          sseUrl = `${window.location.protocol}//${window.location.host}${sseUrl}`;
        }
      }
    }

    const expectedSchemaVersion = Number(process.env.NEXT_PUBLIC_TELEMETRY_SCHEMA_VERSION) || 3;

    return new TelemetryClient({
      sseUrl,
      restUrl,
      expectedSchemaVersion
    });
  }, []);

  useEffect(() => {
    const callbacks: TelemetryClientCallbacks = {
      onStateChange: (state) => {

        setConnectionState(state);
      },
      onError: (err) => {
        if (err) {

        }
        setError(err);
      },
      onSnapshot: (snap) => {

        setSnapshot(snap);
      },
      onHeartbeat: (hb) => {

      }
    };

    client.subscribe(callbacks);
    client.start();

    return () => {
      client.unsubscribe(callbacks);
      client.stop();
    };
  }, [client]);

  // Periodic Freshness check to detect stale snapshots
  useEffect(() => {
    const interval = setInterval(() => {
      if (!snapshot || !snapshot._meta) {
        return;
      }

      const generatedAt = snapshot._meta.generated_at;
      const maxAgeMs = snapshot._meta.max_age_ms || 5000;
      
      const elapsedMs = Date.now() - new Date(generatedAt).getTime();

      // If data is older than double its max age, mark it as stale
      if (elapsedMs > maxAgeMs * 2 && connectionState === "connected") {
        setConnectionState("stale");
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [snapshot, connectionState]);

  const reconnect = () => {
    client.start();
  };

  const lastUpdated = useMemo(() => {
    return snapshot?._meta?.generated_at ? new Date(snapshot._meta.generated_at).getTime() : null;
  }, [snapshot]);

  return (
    <PipelineTelemetryContext.Provider value={{ snapshot, connectionState, error, lastUpdated, reconnect }}>
      {children}
    </PipelineTelemetryContext.Provider>
  );
};

export const usePipelineTelemetry = () => {
  const context = useContext(PipelineTelemetryContext);
  if (context === undefined) {
    throw new Error("usePipelineTelemetry must be used within a PipelineTelemetryProvider");
  }
  return context;
};
