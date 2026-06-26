"use client";

import React, { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge"; // Assume these standard shadcn/radix UI components exist, or fallback to simple styles
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, Globe, Lock, ShieldAlert } from "lucide-react";

export default function CapabilityCatalogPage() {
  const [capabilities, setCapabilities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In a real implementation, this would fetch from /api/v2/admin/capabilities
    // using the shared Axios/Fetch client. For this stub, we use a timeout.
    setTimeout(() => {
      setCapabilities([
        {
          name: "Planner",
          version: "v1",
          visibility: "internal",
          health: "HEALTHY",
          latency_ms: 120,
          circuit_breaker: { failure_threshold: 5 },
          timeouts: { soft_ms: 5000, hard_ms: 10000 },
          dependencies: ["KnowledgeGraph"]
        },
        {
          name: "Research",
          version: "v2",
          visibility: "public",
          health: "HEALTHY",
          latency_ms: 450,
          circuit_breaker: { failure_threshold: 3 },
          timeouts: { soft_ms: 15000, hard_ms: 30000 },
          dependencies: ["WebSearch", "Memory"]
        }
      ]);
      setLoading(false);
    }, 500);
  }, []);

  const getVisibilityIcon = (vis: string) => {
    if (vis === "public") return <Globe className="w-4 h-4 text-emerald-400" />;
    if (vis === "partner") return <ShieldAlert className="w-4 h-4 text-amber-400" />;
    return <Lock className="w-4 h-4 text-rose-400" />;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Capability Catalog</h1>
        <p className="text-slate-400">Living documentation of the AIOS capabilities, metadata, and exposure policies (ADR-0080).</p>
      </div>

      {loading ? (
        <div className="text-slate-400">Loading Capabilities...</div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {capabilities.map((cap) => (
            <div key={cap.name} className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
              <div className="p-6 border-b border-slate-800 flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-bold text-white flex items-center gap-2">
                    {cap.name}
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
                      {cap.version}
                    </span>
                  </h3>
                  <div className="flex items-center gap-2 mt-2 text-sm text-slate-400">
                    {getVisibilityIcon(cap.visibility)}
                    <span className="capitalize">{cap.visibility} Visibility</span>
                  </div>
                </div>
                <div className="px-2 py-1 text-xs font-semibold rounded-md bg-emerald-500/10 text-emerald-400 flex items-center gap-1">
                  <Activity className="w-3 h-3" />
                  {cap.health}
                </div>
              </div>
              <div className="p-6 bg-slate-900/50 space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="block text-slate-500 text-xs">Latency (avg)</span>
                    <span className="text-slate-200">{cap.latency_ms} ms</span>
                  </div>
                  <div>
                    <span className="block text-slate-500 text-xs">Circuit Breaker</span>
                    <span className="text-slate-200">{cap.circuit_breaker.failure_threshold} fails</span>
                  </div>
                  <div>
                    <span className="block text-slate-500 text-xs">Timeouts (Soft/Hard)</span>
                    <span className="text-slate-200">{cap.timeouts.soft_ms}ms / {cap.timeouts.hard_ms}ms</span>
                  </div>
                  <div>
                    <span className="block text-slate-500 text-xs">Dependencies</span>
                    <span className="text-slate-200">{cap.dependencies.join(", ") || "None"}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
