"use client";

import { useState, useEffect, memo } from "react";
import { Activity, AlertCircle, RefreshCw, Cpu, BarChart2 } from "lucide-react";
import { EmptyState, EmptyIllustration } from "@/components/common/EmptyState";
import { 
  PipelineTelemetryProvider, 
  usePipelineTelemetry 
} from "@/components/providers/PipelineTelemetryProvider";
import { 
  TelemetrySnapshotV3, 
  MetricValue 
} from "@/services/telemetryClient";

const MetricCard = memo(function MetricCard({ title, value, label, provenance }: { title: string, value: string | number, label?: string, provenance?: MetricValue<any> }) {
  return (
    <div className="border border-[#1a1a1a] bg-black p-3 relative group">
      <p className="text-[#555] text-[7px] uppercase tracking-wider mb-1 font-bold">{title}</p>
      <div className="flex items-baseline gap-1">
        <p className="text-white font-bold text-lg">{value}</p>
        {label && <span className="text-[9px] text-[#555]">{label}</span>}
      </div>
      {provenance && (
        <div className="absolute top-1 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 text-[6px] text-neutral-500 uppercase tracking-widest bg-black px-1 border border-neutral-800">
          src: {provenance.source} | win: {provenance.window}
        </div>
      )}
    </div>
  );
}, (prev, next) => prev.value === next.value && prev.title === next.title);

const ConnectionBadge = memo(function ConnectionBadge({ connectionState, lastUpdated }: { connectionState: string, lastUpdated: number | null }) {
  const [ageSec, setAgeSec] = useState<number | null>(null);

  useEffect(() => {
    if (!lastUpdated) {
      setAgeSec(null);
      return;
    }
    const update = () => {
      setAgeSec(Math.max(0, Math.round((Date.now() - lastUpdated) / 1000)));
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [lastUpdated]);

  let badgeColor = "bg-emerald-500 animate-pulse";
  let badgeLabel = "LIVE";

  if (connectionState === "reconnecting") {
    badgeColor = "bg-amber-500 animate-pulse";
    badgeLabel = "RECONNECTING";
  } else if (connectionState === "failed") {
    badgeColor = "bg-red-500 animate-pulse";
    badgeLabel = "POLLING MODE - LIVE STREAM UNAVAILABLE";
  } else if (connectionState === "stale") {
    badgeColor = "bg-yellow-500 animate-pulse";
    badgeLabel = "STALE DATA WARNING";
  }

  return (
    <div className="flex items-center gap-3 font-mono text-[8px] tracking-widest uppercase">
      <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${badgeColor}`} />
      <span className="text-white font-bold">{badgeLabel}</span>
      {(connectionState === "connected" || connectionState === "stale") && ageSec !== null && (
        <span className="text-neutral-500 border-l border-neutral-800 pl-3">
          Last Update: {ageSec}s ago
        </span>
      )}
    </div>
  );
});

function PipelineTelemetryDashboard() {
  const { snapshot, connectionState, error, lastUpdated, reconnect } = usePipelineTelemetry();
  const [historyWindow, setHistoryWindow] = useState<"last_24h" | "all_time">("last_24h");

  if (connectionState === "loading" || !snapshot) {
    return (
      <div className="space-y-4 font-mono text-[11px]">
        <div className="h-4 bg-neutral-900 w-48 animate-pulse" />
        <div className="border border-[#1a1a1a] bg-black p-4 h-64 flex flex-col items-center justify-center gap-2">
          {error ? (
            <>
              <AlertCircle className="w-5 h-5 text-red-500 animate-pulse" />
              <span className="text-red-400 tracking-widest uppercase text-center max-w-md">{error}</span>
              <button
                onClick={reconnect}
                className="mt-2 font-mono text-[9px] tracking-widest uppercase bg-white text-black px-2.5 py-0.5 hover:bg-neutral-200 transition-colors"
              >
                Retry Connection
              </button>
            </>
          ) : (
            <>
              <RefreshCw className="w-5 h-5 text-neutral-600 animate-spin" />
              <span className="text-neutral-500 tracking-widest uppercase animate-pulse">Waiting for v3 telemetry heartbeat...</span>
            </>
          )}
        </div>
      </div>
    );
  }

  const histCounts = snapshot.historical[historyWindow];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-[#888]" />
          <h1 className="font-mono text-[11px] tracking-widest uppercase text-white font-bold">
            OBSERVABILITY DASHBOARD
          </h1>
          {snapshot._meta?.schema_version && (
            <span className="ml-2 font-mono text-[8px] bg-[#1a1a1a] text-[#888] px-1.5 py-0.5 rounded">v{snapshot._meta.schema_version}</span>
          )}
        </div>

        <ConnectionBadge connectionState={connectionState} lastUpdated={lastUpdated} />
      </div>

      {error && (
        <div className="border border-amber-500/30 bg-amber-500/5 px-3 py-2 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
            <p className="font-mono text-[10px] text-amber-400">{error}</p>
          </div>
          <button
            onClick={reconnect}
            className="font-mono text-[9px] tracking-widest uppercase bg-white text-black px-2.5 py-0.5 hover:bg-neutral-200 transition-colors"
          >
            Reconnect
          </button>
        </div>
      )}

      {/* PIPELINE ACTIVITY */}
      <section>
        <h2 className="font-mono text-[9px] tracking-widest uppercase text-[#888] font-bold border-b border-[#1a1a1a] pb-1 mb-3">
          Pipeline Activity (CURRENT)
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 font-mono">
          <MetricCard title="Crawler Depth" value={snapshot.current_state.active_crawlers.value} provenance={snapshot.current_state.active_crawlers} />
          <MetricCard title="Celery Queue" value={snapshot.current_state.queue_depth.value} provenance={snapshot.current_state.queue_depth} />
          <MetricCard title="AI Queue" value={snapshot.current_state.ai_queue.value} provenance={snapshot.current_state.ai_queue} />
          <MetricCard title="Active Workers" value={snapshot.current_state.active_workers.value} provenance={snapshot.current_state.active_workers} />
          <MetricCard title="Throughput" value={snapshot.throughput.ingestion_rate_sec.value.toFixed(2)} label="/sec" provenance={snapshot.throughput.ingestion_rate_sec} />
        </div>
      </section>

      {/* PIPELINE QUALITY */}
      <section>
        <h2 className="font-mono text-[9px] tracking-widest uppercase text-[#888] font-bold border-b border-[#1a1a1a] pb-1 mb-3">
          Pipeline Quality
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono">
          <MetricCard title="Thumbnail Coverage" value={`${snapshot.quality.thumbnail_coverage.value.toFixed(1)}%`} provenance={snapshot.quality.thumbnail_coverage} />
          <MetricCard title="Avg Resolution" value={`${Math.round(snapshot.quality.average_resolution.value)}px`} provenance={snapshot.quality.average_resolution} />
          <MetricCard title="Fallback Usage" value={snapshot.quality.fallback_usage.value} provenance={snapshot.quality.fallback_usage} />
          <MetricCard title="Avg Ranking Score" value={snapshot.quality.average_ranking_score.value.toFixed(1)} provenance={snapshot.quality.average_ranking_score} />
        </div>
      </section>

      {/* HISTORICAL STATISTICS */}
      <section>
        <div className="flex items-center justify-between border-b border-[#1a1a1a] pb-1 mb-3">
          <h2 className="font-mono text-[9px] tracking-widest uppercase text-[#888] font-bold">
            Historical Statistics
          </h2>
          <div className="flex gap-1 font-mono text-[8px] uppercase">
             <button 
                onClick={() => setHistoryWindow("last_24h")}
                className={`px-2 py-0.5 border transition-colors ${historyWindow === "last_24h" ? "border-emerald-500/50 text-emerald-400 bg-emerald-500/10" : "border-[#1a1a1a] text-[#555] hover:text-white"}`}
             >
                Last 24H
             </button>
             <button 
                onClick={() => setHistoryWindow("all_time")}
                className={`px-2 py-0.5 border transition-colors ${historyWindow === "all_time" ? "border-emerald-500/50 text-emerald-400 bg-emerald-500/10" : "border-[#1a1a1a] text-[#555] hover:text-white"}`}
             >
                All Time
             </button>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-2 font-mono">
           <MetricCard title="Discovered" value={histCounts.discovered} />
           <MetricCard title="Fetched" value={histCounts.fetched} />
           <MetricCard title="Filtered" value={histCounts.filtered} />
           <MetricCard title="Deduplicated" value={histCounts.deduplicated} />
           <MetricCard title="Processed" value={histCounts.processed} />
           <MetricCard title="Published" value={histCounts.published} />
        </div>
      </section>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* AI ENGINE */}
        <section className="relative">
          <h2 className="font-mono text-[9px] tracking-widest uppercase text-[#888] font-bold border-b border-[#1a1a1a] pb-1 mb-3 flex justify-between">
            <span>AI Engine</span>
            <span className={snapshot.ai_engine.enabled ? "text-emerald-400" : "text-amber-500"}>
               {snapshot.ai_engine.enabled ? "ENABLED" : "DISABLED"}
            </span>
          </h2>
          {snapshot.ai_engine.enabled ? (
            <div className="grid grid-cols-2 gap-3 font-mono">
               <MetricCard title="Provider" value={snapshot.ai_engine.provider_name} label={snapshot.ai_engine.provider_model} />
               <MetricCard title="Success Rate" value={`${(snapshot.ai_engine.success_rate.value * 100).toFixed(1)}%`} provenance={snapshot.ai_engine.success_rate} />
               <MetricCard title="Cost (Today)" value={`$${snapshot.ai_engine.cost_usd_today.value.toFixed(2)}`} provenance={snapshot.ai_engine.cost_usd_today} />
               <MetricCard title="Latency (p95)" value={`${(snapshot.ai_engine.average_latency_p95.value / 1000).toFixed(2)}s`} provenance={snapshot.ai_engine.average_latency_p95} />
            </div>
          ) : (
            <EmptyState size="sm" className="border border-dashed border-[#333] bg-[#0c0c0c]">
               <EmptyIllustration
                  icon={Cpu}
                  title="AI Metrics Disabled"
                  description="Provider not configured. Configure provider to collect AI metrics."
               />
            </EmptyState>
          )}
        </section>

        {/* RANKING ENGINE */}
        <section className="relative">
          <h2 className="font-mono text-[9px] tracking-widest uppercase text-[#888] font-bold border-b border-[#1a1a1a] pb-1 mb-3 flex justify-between">
            <span>Ranking Engine</span>
            <span className={snapshot.ranking_engine.enabled ? "text-emerald-400" : "text-amber-500"}>
               {snapshot.ranking_engine.enabled ? "ENABLED" : "DISABLED"}
            </span>
          </h2>
          {snapshot.ranking_engine.enabled ? (
            <div className="grid grid-cols-2 gap-3 font-mono">
               <MetricCard title="Evaluated" value={snapshot.ranking_engine.articles_evaluated.value} provenance={snapshot.ranking_engine.articles_evaluated} />
               <MetricCard title="Active Signals" value={snapshot.ranking_engine.active_articles.value} provenance={snapshot.ranking_engine.active_articles} />
               <MetricCard title="Expired Signals" value={snapshot.ranking_engine.expired_articles.value} provenance={snapshot.ranking_engine.expired_articles} />
               <MetricCard title="Last Run" value={snapshot.ranking_engine.last_run ? new Date(snapshot.ranking_engine.last_run).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "NEVER EXECUTED"} />
            </div>
          ) : (
            <EmptyState size="sm" className="border border-dashed border-[#333] bg-[#0c0c0c]">
               <EmptyIllustration
                  icon={BarChart2}
                  title="Ranking Disabled"
                  description="Waiting for next engine execution."
               />
            </EmptyState>
          )}
        </section>
      </div>
    </div>
  );
}

export default function AdminTelemetryPage() {
  return (
    <PipelineTelemetryProvider>
      <PipelineTelemetryDashboard />
    </PipelineTelemetryProvider>
  );
}
