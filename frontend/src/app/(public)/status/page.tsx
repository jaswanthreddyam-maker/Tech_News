import React from "react";
import { Activity, CheckCircle2, Server, Database, Radio } from "lucide-react";

export const metadata = {
  title: "System Status | Tech News Today",
  description: "Realtime infrastructure status and service health telemetry for Tech News Today.",
};

export default function StatusPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-foreground space-y-10">
      <div className="space-y-4 border-b border-border/40 pb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-mono tracking-widest uppercase">
          <Activity className="w-3.5 h-3.5" /> All Systems Operational
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
          System Status
        </h1>
        <p className="text-muted-foreground">Real-time infrastructure health monitor</p>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between p-4 rounded-xl border border-border/60 bg-card/40">
          <div className="flex items-center gap-3">
            <Server className="w-5 h-5 text-emerald-400" />
            <span className="font-semibold text-sm">FastAPI REST Engine</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-emerald-400 font-mono">
            <CheckCircle2 className="w-4 h-4" /> Operational
          </div>
        </div>

        <div className="flex items-center justify-between p-4 rounded-xl border border-border/60 bg-card/40">
          <div className="flex items-center gap-3">
            <Radio className="w-5 h-5 text-emerald-400" />
            <span className="font-semibold text-sm">Celery Background Workers</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-emerald-400 font-mono">
            <CheckCircle2 className="w-4 h-4" /> Operational
          </div>
        </div>

        <div className="flex items-center justify-between p-4 rounded-xl border border-border/60 bg-card/40">
          <div className="flex items-center gap-3">
            <Database className="w-5 h-5 text-emerald-400" />
            <span className="font-semibold text-sm">Supabase PostgreSQL & pgvector</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-emerald-400 font-mono">
            <CheckCircle2 className="w-4 h-4" /> Operational
          </div>
        </div>

        <div className="flex items-center justify-between p-4 rounded-xl border border-border/60 bg-card/40">
          <div className="flex items-center gap-3">
            <Activity className="w-5 h-5 text-emerald-400" />
            <span className="font-semibold text-sm">Railway Redis Broker & Cache</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-emerald-400 font-mono">
            <CheckCircle2 className="w-4 h-4" /> Operational
          </div>
        </div>
      </div>
    </div>
  );
}
