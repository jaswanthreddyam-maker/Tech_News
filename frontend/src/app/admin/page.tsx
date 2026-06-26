"use client";

import { useEffect, useState, useRef } from "react";
import { apiFetch } from "../../services/api";
import { fetchInfrastructureHealth } from "@/lib/api/normalizers/infrastructure";
import {
  Activity,
  Database,
  Radio,
  Cpu,
  Server,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { getHealthColor, getHealthLabel } from "@/lib/health/status";

interface ServiceState {
  service: string;
  status: "ONLINE" | "DEGRADED" | "OFFLINE" | "UNKNOWN" | "DELAYED" | "ERROR";
  available?: boolean;
  status_reason?: string;
  latency_ms: number;
  last_checked: string;
  last_success?: string;
  error?: string;
}

interface HistorySample {
  timestamp: string;
  status: string;
  latency_ms: number;
}

interface ServiceContainer {
  snapshot: ServiceState;
  history: HistorySample[];
}

interface InfraPayload {
  health_score: {
    score: number;
    grade: string;
    calculated_at: string;
  };
  services: {
    postgres: ServiceContainer;
    redis: ServiceContainer;
    worker: ServiceContainer;
    beat: ServiceContainer;
    backend: ServiceContainer;
  };
}

interface QueuePayload {
  status: string;
  available?: boolean;
  status_reason?: string;
  last_checked: string;
  metrics: {
    queue_depth: number;
    processing_rate_jobs_min: number;
    growth_rate_jobs_5s: number;
  };
}

interface OverviewPayload {
  source_health: {
    total: number;
    healthy: number;
    degraded: number;
    failed: number;
  };
  article_pipeline: {
    raw: number;
    processed: number;
    published: number;
    draft: number;
    rejected: number;
  };
  ai_queue: {
    queued: number;
    processing: number;
    completed: number;
    failed: number;
    retry: number;
  };
  thumbnail_metrics?: {
    success_rate: number;
    download_failures: number;
    processing_queue: number;
    thumbnail_quality_score: number;
    fallback_rate: number;
    fallback_health: string;
    source_distribution: Record<string, number>;
  };
  emergency_cutoff_active: boolean;
}

interface LiveEvent {
  time: string;
  agent: string;
  msg: string;
  status?: string;
}

function MetricBox({
  label,
  value,
  color = "text-white",
  pulse = false,
}: {
  label: string;
  value: number | string;
  color?: string;
  pulse?: boolean;
}) {
  return (
    <div className="border border-[#1a1a1a] bg-[#080808] p-3">
      <p className="font-mono text-[8px] tracking-widest uppercase text-[#555] mb-1">{label}</p>
      <p className={`font-mono text-xl font-bold ${color} ${pulse ? "animate-pulse" : ""}`}>
        {value}
      </p>
    </div>
  );
}

function InfraStatus({
  label,
  status,
  available,
  status_reason,
  latency,
  last_checked,
  last_success,
  history = [],
}: {
  label: string;
  status?: string;
  available?: boolean;
  status_reason?: string;
  latency?: number;
  last_checked?: string;
  last_success?: string;
  history?: HistorySample[];
}) {
  const { dotColor, textColor } = getHealthColor(status);
  const labelText = getHealthLabel(status);

  const tooltip = `Service: ${label}
Status: ${labelText}
Reason: ${status_reason || "N/A"}
Latency: ${latency !== undefined ? latency + 'ms' : 'N/A'}
Last Checked: ${last_checked ? new Date(last_checked).toLocaleString() : 'N/A'}
Last Success: ${last_success ? new Date(last_success).toLocaleString() : 'N/A'}`;

  return (
    <div className="border-b border-[#111] py-2 cursor-help" title={tooltip}>
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 shrink-0 ${dotColor}`} />
        <span className="font-mono text-[10px] text-[#ccc]">{label}</span>
        {status?.toUpperCase() !== "OFFLINE" && status?.toUpperCase() !== "ERROR" && latency !== undefined && latency !== null && latency > 0 && (
          <span className="font-mono text-[8px] text-[#555]">({latency}ms)</span>
        )}
        <span
          className={`ml-auto font-mono text-[8px] tracking-widest uppercase ${textColor}`}
        >
          {labelText}
        </span>
      </div>
      
      {/* 10-sample rolling history dots */}
      {history && history.length > 0 && (
        <div className="flex items-center gap-1 mt-1 pl-4">
          <span className="font-mono text-[7px] text-[#444] mr-1">HIST:</span>
          {[...history].reverse().map((h, i) => {
            const hStatus = (h.status || "").toUpperCase();
            let c = "bg-[#333]";
            if (hStatus === "ONLINE") c = "bg-emerald-500/60";
            else if (hStatus === "DELAYED") c = "bg-orange-500/60";
            else if (hStatus === "DEGRADED") c = "bg-amber-500/60";
            else if (hStatus === "OFFLINE" || hStatus === "ERROR") c = "bg-red-500/60";
            return (
              <span
                key={i}
                className={`h-1 w-1 rounded-sm ${c}`}
                title={`Checked: ${new Date(h.timestamp).toLocaleTimeString()}
Latency: ${h.latency_ms}ms
Status: ${hStatus}`}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="border border-[#1a1a1a] bg-[#0c0c0c] p-4 animate-pulse">
      <div className="h-3 bg-neutral-900 w-1/3 mb-3" />
      <div className="grid grid-cols-2 gap-2">
        <div className="h-14 bg-neutral-900" />
        <div className="h-14 bg-neutral-900" />
        <div className="h-14 bg-neutral-900" />
        <div className="h-14 bg-neutral-900" />
      </div>
    </div>
  );
}

export default function AdminDashboardPage() {
  const [overview, setOverview] = useState<OverviewPayload | null>(null);
  const [infra, setInfra] = useState<InfraPayload | null>(null);
  const [queue, setQueue] = useState<QueuePayload | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const feedRef = useRef<HTMLDivElement>(null);

  const fetchOverview = async () => {
    try {
      const result = await apiFetch<any>("/admin/overview");

      if (result && result.data) {

        setOverview(result.data);
      } else {

      }
    } catch (err: any) {

      setError("Failed to connect to monitoring platform API.");
    }
  };

  const fetchInfra = async () => {
    try {
      const payload = await fetchInfrastructureHealth();
      setInfra(payload as any);
    } catch (err: any) {

    }
  };

  const fetchQueue = async () => {
    try {
      const result = await apiFetch<any>("/admin/queue");

      if (result && result.data) {

        setQueue(result.data);
      } else {

      }
    } catch (err: any) {

    }
  };

  const fetchLogs = async () => {
    try {
      const result = await apiFetch<any[]>("/admin/logs");
      if (result && Array.isArray(result)) {
        const initialEvents = result.map((parsed: any) => ({
          time: parsed.timestamp || new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" }),
          agent: parsed.agent,
          msg: parsed.msg,
          status: parsed.status,
        }));
        setEvents(initialEvents);
      }
    } catch (err) {

    }
  };

  const handleManualRefresh = async () => {
    setRefreshing(true);
    try {
      await Promise.all([fetchOverview(), fetchInfra(), fetchQueue(), fetchLogs()]);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard data.");
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    const init = async () => {
      try {
        await Promise.all([fetchOverview(), fetchInfra(), fetchQueue(), fetchLogs()]);
      } catch (e) {
        // Catch gracefully
      } finally {
        setLoading(false);
      }
    };

    init();

    // Independent polling rates
    const queueInterval = setInterval(fetchQueue, 5000); // Queue is 5s
    const infraInterval = setInterval(fetchInfra, 10000); // Infra checks is 10s
    const overviewInterval = setInterval(fetchOverview, 60000); // Overview checks is 60s

    return () => {
      clearInterval(queueInterval);
      clearInterval(infraInterval);
      clearInterval(overviewInterval);
    };
  }, []);

  // SSE for live operations feed (Initial Load then stream forever)
  useEffect(() => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
    let sseUrl = `${apiBase}/events/stream`;
    if (typeof window !== "undefined") {
      if (sseUrl.startsWith("/")) {
        sseUrl = `${window.location.protocol}//${window.location.host}${sseUrl}`;
      }
      if (sseUrl.includes(":3000")) {
        sseUrl = sseUrl.replace(":3000", "");
      }
    }

    let eventSource: EventSource | null = null;
    let reconnectDelay = 1000;
    let reconnectTimer: NodeJS.Timeout | null = null;

    const connect = () => {
      if (eventSource) eventSource.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);

      eventSource = new EventSource(sseUrl);

      eventSource.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          if (parsed.agent && parsed.msg) {
            const entry: LiveEvent = {
              time: parsed.time || new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" }),
              agent: parsed.agent,
              msg: parsed.msg,
              status: parsed.status,
            };
            setEvents((prev) => [entry, ...prev.slice(0, 49)]);
          }
        } catch {
          // Skip non-JSON keepalives
        }
      };

      eventSource.onerror = () => {
        eventSource?.close();
        reconnectTimer = setTimeout(() => {
          reconnectDelay = Math.min(reconnectDelay * 2, 30000);
          connect();
        }, reconnectDelay);
      };

      eventSource.onopen = () => {
        reconnectDelay = 1000;
      };
    };

    connect();

    return () => {
      if (eventSource) eventSource.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, []);

  const healthScore = infra?.health_score;

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="h-5 bg-neutral-900 w-48 animate-pulse" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <div className="border border-[#1a1a1a] bg-black p-4 h-64 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with high level grade and score */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 ${healthScore && healthScore.score < 80 ? "bg-red-500" : "bg-emerald-500"} animate-pulse`} />
          <h1 className="font-mono text-[11px] tracking-widest uppercase text-white font-bold">
            COMMAND CENTER {healthScore && `| HEALTH: ${healthScore.score}% (${healthScore.grade})`}
          </h1>
        </div>
        <button
          onClick={handleManualRefresh}
          disabled={refreshing}
          className="flex items-center gap-1.5 font-mono text-[9px] tracking-widest uppercase text-[#888] hover:text-white transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${refreshing ? "animate-spin" : ""}`} />
          REFRESH
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="border border-red-500/30 bg-red-500/5 px-3 py-2 flex items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
          <p className="font-mono text-[10px] text-red-400">{error}</p>
        </div>
      )}

      {overview && (
        <>
          {/* Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-4">
            {/* SOURCE HEALTH */}
            <div className="border border-[#1a1a1a] bg-[#0c0c0c] p-4">
              <div className="flex items-center gap-2 mb-3">
                <Radio className="w-3.5 h-3.5 text-[#888]" />
                <h3 className="font-mono text-[9px] tracking-widest uppercase text-[#888] font-bold">
                  SOURCE HEALTH
                </h3>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <MetricBox label="Total" value={overview.source_health.total} />
                <MetricBox label="Healthy" value={overview.source_health.healthy} color="text-emerald-400" />
                <MetricBox label="Degraded" value={overview.source_health.degraded} color="text-amber-400" />
                <MetricBox label="Failed" value={overview.source_health.failed} color="text-red-400" />
              </div>
            </div>

            {/* ARTICLE PIPELINE */}
            <div className="border border-[#1a1a1a] bg-[#0c0c0c] p-4">
              <div className="flex items-center gap-2 mb-3">
                <Database className="w-3.5 h-3.5 text-[#888]" />
                <h3 className="font-mono text-[9px] tracking-widest uppercase text-[#888] font-bold">
                  ARTICLE PIPELINE
                </h3>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <MetricBox label="Raw" value={overview.article_pipeline.raw} />
                <MetricBox label="Processed" value={overview.article_pipeline.processed} />
                <MetricBox label="Published" value={overview.article_pipeline.published} color="text-emerald-400" />
                <MetricBox label="Rejected" value={overview.article_pipeline.rejected} color="text-red-400" />
              </div>
            </div>

            {/* AI QUEUE */}
            <div className="border border-[#1a1a1a] bg-[#0c0c0c] p-4">
              <div className="flex items-center gap-2 mb-3">
                <Cpu className="w-3.5 h-3.5 text-[#888]" />
                <h3 className="font-mono text-[9px] tracking-widest uppercase text-[#888] font-bold">
                  AI QUEUE
                </h3>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <MetricBox label="Queued" value={overview.ai_queue.queued} />
                <MetricBox label="Processing" value={overview.ai_queue.processing} color="text-blue-400" pulse={overview.ai_queue.processing > 0} />
                <MetricBox label="Completed" value={overview.ai_queue.completed} color="text-emerald-400" />
                <MetricBox label="Failed" value={overview.ai_queue.failed} color="text-red-400" />
              </div>
            </div>

            {/* INFRASTRUCTURE */}
            <div className="border border-[#1a1a1a] bg-[#0c0c0c] p-4">
              <div className="flex items-center gap-2 mb-3">
                <Server className="w-3.5 h-3.5 text-[#888]" />
                <h3 className="font-mono text-[9px] tracking-widest uppercase text-[#888] font-bold">
                  INFRASTRUCTURE
                </h3>
              </div>
              <div className="space-y-0.5">
                <InfraStatus
                  label="PostgreSQL"
                  status={infra?.services?.postgres?.snapshot?.status}
                  available={infra?.services?.postgres?.snapshot?.available}
                  status_reason={infra?.services?.postgres?.snapshot?.status_reason}
                  latency={infra?.services?.postgres?.snapshot?.latency_ms}
                  last_checked={infra?.services?.postgres?.snapshot?.last_checked}
                  last_success={infra?.services?.postgres?.snapshot?.last_success}
                  history={infra?.services?.postgres?.history}
                />
                <InfraStatus
                  label="Redis"
                  status={infra?.services?.redis?.snapshot?.status}
                  available={infra?.services?.redis?.snapshot?.available}
                  status_reason={infra?.services?.redis?.snapshot?.status_reason}
                  latency={infra?.services?.redis?.snapshot?.latency_ms}
                  last_checked={infra?.services?.redis?.snapshot?.last_checked}
                  last_success={infra?.services?.redis?.snapshot?.last_success}
                  history={infra?.services?.redis?.history}
                />
                <InfraStatus
                  label="Worker Engine"
                  status={infra?.services?.worker?.snapshot?.status}
                  available={infra?.services?.worker?.snapshot?.available}
                  status_reason={infra?.services?.worker?.snapshot?.status_reason}
                  latency={infra?.services?.worker?.snapshot?.latency_ms}
                  last_checked={infra?.services?.worker?.snapshot?.last_checked}
                  last_success={infra?.services?.worker?.snapshot?.last_success}
                  history={infra?.services?.worker?.history}
                />
                <InfraStatus
                  label="Scheduler Beat"
                  status={infra?.services?.beat?.snapshot?.status}
                  available={infra?.services?.beat?.snapshot?.available}
                  status_reason={infra?.services?.beat?.snapshot?.status_reason}
                  latency={infra?.services?.beat?.snapshot?.latency_ms}
                  last_checked={infra?.services?.beat?.snapshot?.last_checked}
                  last_success={infra?.services?.beat?.snapshot?.last_success}
                  history={infra?.services?.beat?.history}
                />
                <InfraStatus
                  label="Backend API"
                  status={infra?.services?.backend?.snapshot?.status}
                  available={infra?.services?.backend?.snapshot?.available}
                  status_reason={infra?.services?.backend?.snapshot?.status_reason}
                  latency={infra?.services?.backend?.snapshot?.latency_ms}
                  last_checked={infra?.services?.backend?.snapshot?.last_checked}
                  last_success={infra?.services?.backend?.snapshot?.last_success}
                  history={infra?.services?.backend?.history}
                />
                <InfraStatus
                  label="Celery Queue"
                  status={queue?.status}
                  available={queue?.available}
                  status_reason={queue?.status_reason}
                  latency={queue?.metrics?.queue_depth}
                  last_checked={queue?.last_checked}
                  last_success={queue?.last_checked}
                />
              </div>
            </div>

            {/* THUMBNAIL HEALTH */}
            {overview.thumbnail_metrics && (
              <div className="border border-[#1a1a1a] bg-[#0c0c0c] p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Activity className="w-3.5 h-3.5 text-[#888]" />
                  <h3 className="font-mono text-[9px] tracking-widest uppercase text-[#888] font-bold">
                    THUMBNAIL HEALTH
                  </h3>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <MetricBox label="Coverage %" value={`${overview.thumbnail_metrics.success_rate.toFixed(1)}%`} color="text-emerald-400" />
                  <MetricBox label="Failures" value={overview.thumbnail_metrics.download_failures} color={overview.thumbnail_metrics.download_failures > 0 ? "text-amber-400" : "text-emerald-400"} />
                  <MetricBox label="Fallback %" value={`${overview.thumbnail_metrics.fallback_rate.toFixed(1)}%`} color={overview.thumbnail_metrics.fallback_health === "Critical" ? "text-red-400" : "text-amber-400"} />
                  <MetricBox label="Quality Score" value={overview.thumbnail_metrics.thumbnail_quality_score} color="text-blue-400" />
                </div>
              </div>
            )}
          </div>

          {/* LIVE OPERATIONS FEED */}
          <div className="border border-[#1a1a1a] bg-black">
            <div className="px-4 py-2.5 border-b border-[#1a1a1a] flex items-center gap-2">
              <span className="h-1.5 w-1.5 bg-emerald-500 animate-pulse" />
              <h3 className="font-mono text-[9px] tracking-widest uppercase text-[#888] font-bold">
                LIVE OPERATIONS FEED
              </h3>
              <span className="font-mono text-[8px] text-[#333] ml-auto">
                {events.length} EVENTS
              </span>
            </div>
            <div
              ref={feedRef}
              className="h-64 overflow-y-auto p-3 space-y-0.5"
            >
              {events.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <p className="font-mono text-[10px] text-[#333]">
                    Awaiting event stream connection...
                  </p>
                </div>
              ) : (
                events.map((event, idx) => (
                  <div key={idx} className="flex items-start gap-2 font-mono text-[11px] leading-relaxed">
                    <span className="text-[#555] shrink-0" suppressHydrationWarning>
                      [{event.time}]
                    </span>
                    <span className="text-emerald-400 shrink-0">{event.agent}:</span>
                    <span className="text-[#ccc]">{event.msg}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
