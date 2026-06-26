"use client";

import { useEffect, useState } from "react";

// --- Types ---
type HealthStatus = "healthy" | "degraded" | "unhealthy" | "offline" | "error";

interface CQRSHealth {
  status: HealthStatus;
  projection_lag: number;
  outbox_backlog: number;
  missing_impact_scores: number;
  missing_summaries: number;
  missing_thumbnails: number;
  projection_success_rate: string;
}

interface WorkerHealth {
  celery_worker: HealthStatus;
  celery_beat: HealthStatus;
  sse_stream: HealthStatus;
}

interface QueueHealth {
  rss_queue_depth: number;
  projection_queue_depth: number;
  thumbnail_queue_depth: number;
  embedding_queue_depth: number;
}

interface SourceHealth {
  total_sources: number;
  healthy_sources: number;
  degraded_sources: number;
  avg_fetch_latency_ms: number;
}

interface RecoveryHealth {
  status: HealthStatus;
  automation_enabled: boolean;
  recovery_state: string;
  cooldown_active: boolean;
  attempts_last_hour: number;
  success_rate: number;
  consecutive_failures: number;
  mode: string;
  last_recovery: string;
}

interface IncidentHealth {
  open_incidents: number;
  auto_resolved: number;
  manual_intervention: number;
  top_cause: string;
  average_confidence: string;
  latest_explanation: {
    top_incident: string;
    ai_summary: string;
    confidence: string;
  } | null;
}

interface NewsletterStats {
  total_subscribers: number;
  pending_subscribers: number;
  confirmed_subscribers: number;
  unsubscribed: number;
  confirmation_rate: number;
  new_today: number;
}

interface CertificationStatus {
  last_run: string;
  type: string;
  grade: string;
  pass_rate: number;
  recent_runs: {
    run_id: string;
    type: string;
    passed: number;
    failed: number;
    grade: string;
    completed_at: string;
  }[];
}

// --- Helper Functions ---
function getStatusColor(status: HealthStatus): string {
  switch (status) {
    case "healthy": return "border-green-500 bg-green-500/10 text-green-500";
    case "degraded": return "border-yellow-500 bg-yellow-500/10 text-yellow-500";
    case "unhealthy":
    case "error":
    case "offline": return "border-red-500 bg-red-500/10 text-red-500";
    default: return "border-neutral-500 bg-neutral-500/10 text-neutral-500";
  }
}

function getIndicatorColor(status: HealthStatus): string {
  switch (status) {
    case "healthy": return "bg-green-500";
    case "degraded": return "bg-yellow-500";
    case "unhealthy":
    case "error":
    case "offline": return "bg-red-500";
    default: return "bg-neutral-500";
  }
}

// ---------------------------------------------------------
// Components
// ---------------------------------------------------------

function HealthCard({ title, status, children }: { title: string, status: HealthStatus, children: React.ReactNode }) {
  const colorClass = getStatusColor(status);
  const indicatorClass = getIndicatorColor(status);

  return (
    <div className={`p-6 rounded-xl border-2 transition-colors ${colorClass}`}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold tracking-tight">{title}</h2>
        <div className={`h-3 w-3 rounded-full ${indicatorClass} animate-pulse`} />
      </div>
      <div className="space-y-2 text-sm">
        {children}
      </div>
    </div>
  );
}

// ---------------------------------------------------------
// Main Page
// ---------------------------------------------------------

export default function OperationsDashboard() {
  const [cqrs, setCqrs] = useState<CQRSHealth | null>(null);
  const [workers, setWorkers] = useState<WorkerHealth | null>(null);
  const [queues, setQueues] = useState<QueueHealth | null>(null);
  const [sources, setSources] = useState<SourceHealth | null>(null);
  const [recovery, setRecovery] = useState<RecoveryHealth | null>(null);
  const [incidents, setIncidents] = useState<IncidentHealth | null>(null);
  const [newsletter, setNewsletter] = useState<NewsletterStats | null>(null);
  const [certification, setCertification] = useState<CertificationStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const [cqrsRes, workersRes, queuesRes, sourcesRes, recoveryRes, incidentRes, newsletterRes, certRes] = await Promise.all([
          fetch("/api/v1/health/cqrs").catch(() => null),
          fetch("/api/v1/health/workers").catch(() => null),
          fetch("/api/v1/health/queues").catch(() => null),
          fetch("/api/v1/health/sources").catch(() => null),
          fetch("/api/v1/health/recovery").catch(() => null),
          fetch("/api/v1/health/incidents").catch(() => null),
          fetch("/api/v1/newsletter/stats").catch(() => null),
          fetch("/api/v1/certification/status").catch(() => null)
        ]);

        if (cqrsRes?.ok) {
          const data = await cqrsRes.json();
          setCqrs(data.data);
        }
        
        if (workersRes?.ok) {
          const data = await workersRes.json();
          setWorkers(data.data);
        }
        
        if (queuesRes?.ok) {
          const data = await queuesRes.json();
          setQueues(data.data);
        }
        
        if (sourcesRes?.ok) {
          const data = await sourcesRes.json();
          setSources(data.data);
        }
        
        if (recoveryRes?.ok) {
          const data = await recoveryRes.json();
          setRecovery(data.data);
        }
        
        if (incidentRes?.ok) {
          const data = await incidentRes.json();
          setIncidents(data.data);
        }
        
        if (newsletterRes?.ok) {
          const data = await newsletterRes.json();
          setNewsletter(data);
        }
        
        if (certRes?.ok) {
          const data = await certRes.json();
          setCertification(data);
        }
      } catch (err) {
        console.error("Failed to fetch operational health", err);
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
    
    // Auto-refresh every 5 seconds to provide near real-time visibility
    const interval = setInterval(fetchHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !cqrs) {
    return <div className="p-12 text-center text-neutral-400">Loading Operational Health...</div>;
  }

  // Derived statuses (Fallback to error if missing)
  const cqrsStatus: HealthStatus = cqrs ? cqrs.status : "error";
  
  // Workers overall status
  let workerStatus: HealthStatus = "healthy";
  if (workers) {
    if (workers.celery_worker !== "healthy" || workers.celery_beat !== "healthy" || workers.sse_stream !== "healthy") {
        workerStatus = "degraded";
    }
    if (workers.celery_worker === "unhealthy" || workers.celery_worker === "offline") {
        workerStatus = "unhealthy";
    }
  } else {
    workerStatus = "error";
  }

  // Queue status (Arbitrary thresholds for Sprint 1)
  let queueStatus: HealthStatus = "healthy";
  if (queues) {
    const total = queues.rss_queue_depth + queues.projection_queue_depth + queues.thumbnail_queue_depth + queues.embedding_queue_depth;
    if (total > 50) queueStatus = "degraded";
    if (total > 200) queueStatus = "unhealthy";
  } else {
    queueStatus = "error";
  }

  // Source status
  let sourceStatus: HealthStatus = "healthy";
  if (sources) {
    if (sources.degraded_sources > 0) sourceStatus = "degraded";
    if (sources.healthy_sources === 0) sourceStatus = "unhealthy";
  } else {
    sourceStatus = "error";
  }

  // Determine Platform Status
  let platformStatus: HealthStatus = "healthy";
  let recoveryStatus: HealthStatus = recovery ? recovery.status : "error";

  if (
    cqrsStatus === "unhealthy" || cqrsStatus === "error" ||
    workerStatus === "unhealthy" || workerStatus === "error" ||
    queueStatus === "unhealthy" || queueStatus === "error" ||
    sourceStatus === "unhealthy" || sourceStatus === "error" ||
    recoveryStatus === "error" || recoveryStatus === "unhealthy"
  ) {
    platformStatus = "unhealthy";
  } else if (
    cqrsStatus === "degraded" ||
    workerStatus === "degraded" ||
    queueStatus === "degraded" ||
    sourceStatus === "degraded" ||
    recoveryStatus === "degraded"
  ) {
    platformStatus = "degraded";
  }

  const platformTitle = platformStatus === "healthy" ? "PLATFORM HEALTHY" : platformStatus === "degraded" ? "PLATFORM DEGRADED" : "PLATFORM UNHEALTHY";

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tighter">Operations Dashboard</h1>
        <p className="text-neutral-400 mt-2">Real-time internal system health and CQRS status.</p>
      </div>

      {/* Global Platform Status */}
      <HealthCard title={`Global Status: ${platformTitle}`} status={platformStatus}>
        <div className="flex justify-between"><span>CQRS:</span> <strong className="uppercase">{cqrsStatus}</strong></div>
        <div className="flex justify-between"><span>Workers:</span> <strong className="uppercase">{workerStatus}</strong></div>
        <div className="flex justify-between"><span>Queues:</span> <strong className="uppercase">{queueStatus}</strong></div>
        <div className="flex justify-between"><span>Sources:</span> <strong className="uppercase">{sourceStatus}</strong></div>
        <div className="flex justify-between"><span>Recovery:</span> <strong className="uppercase">{recoveryStatus}</strong></div>
      </HealthCard>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        
        {/* CQRS Card */}
        <HealthCard title="CQRS Health" status={cqrsStatus}>
          {cqrs ? (
            <>
              <div className="flex justify-between"><span>Projection Lag:</span> <strong>{cqrs.projection_lag}</strong></div>
              <div className="flex justify-between"><span>Outbox Backlog:</span> <strong>{cqrs.outbox_backlog}</strong></div>
              <div className="flex justify-between"><span>Missing Impact:</span> <strong>{cqrs.missing_impact_scores}</strong></div>
              <div className="flex justify-between"><span>Missing Thumbnails:</span> <strong>{cqrs.missing_thumbnails}</strong></div>
              <div className="flex justify-between"><span>Success Rate:</span> <strong>{cqrs.projection_success_rate}</strong></div>
            </>
          ) : (
            <div>Service Unreachable</div>
          )}
        </HealthCard>

        {/* Workers Card */}
        <HealthCard title="Worker Health" status={workerStatus}>
          {workers ? (
            <>
              <div className="flex justify-between"><span>Celery Worker:</span> <strong className="uppercase">{workers.celery_worker}</strong></div>
              <div className="flex justify-between"><span>Celery Beat:</span> <strong className="uppercase">{workers.celery_beat}</strong></div>
              <div className="flex justify-between"><span>SSE Stream:</span> <strong className="uppercase">{workers.sse_stream}</strong></div>
            </>
          ) : (
            <div>Service Unreachable</div>
          )}
        </HealthCard>

        {/* Queues Card */}
        <HealthCard title="Queue Status" status={queueStatus}>
          {queues ? (
            <>
              <div className="flex justify-between"><span>RSS Ingestion:</span> <strong>{queues.rss_queue_depth}</strong></div>
              <div className="flex justify-between"><span>Projection:</span> <strong>{queues.projection_queue_depth}</strong></div>
              <div className="flex justify-between"><span>Thumbnails:</span> <strong>{queues.thumbnail_queue_depth}</strong></div>
              <div className="flex justify-between"><span>Embeddings:</span> <strong>{queues.embedding_queue_depth}</strong></div>
            </>
          ) : (
            <div>Service Unreachable</div>
          )}
        </HealthCard>

        {/* Sources Card */}
        <HealthCard title="Source Health" status={sourceStatus}>
          {sources ? (
            <>
              <div className="flex justify-between"><span>Total Sources:</span> <strong>{sources.total_sources}</strong></div>
              <div className="flex justify-between"><span>Healthy:</span> <strong>{sources.healthy_sources}</strong></div>
              <div className="flex justify-between"><span>Degraded:</span> <strong>{sources.degraded_sources}</strong></div>
              <div className="flex justify-between"><span>Avg Latency:</span> <strong>{sources.avg_fetch_latency_ms}ms</strong></div>
            </>
          ) : (
            <div>Service Unreachable</div>
          )}
        </HealthCard>

        {/* Autonomous Recovery Card */}
        <HealthCard title="Autonomous Recovery" status={recoveryStatus}>
          {recovery ? (
            <>
              <div className="flex justify-between"><span>Mode:</span> <strong className="uppercase">{recovery.mode.replace("_", " ")}</strong></div>
              <div className="flex justify-between"><span>State:</span> <strong className="uppercase text-xs mt-1">{recovery.recovery_state}</strong></div>
              <div className="flex justify-between text-neutral-400 border-t border-white/5 pt-2 mt-2"><span>Attempts (1h):</span> <strong>{recovery.attempts_last_hour} / 3</strong></div>
              <div className="flex justify-between text-neutral-400"><span>Consecutive Fails:</span> <strong>{recovery.consecutive_failures} / 3</strong></div>
              <div className="flex justify-between text-neutral-400"><span>Cooldown Active:</span> <strong>{recovery.cooldown_active ? "YES" : "NO"}</strong></div>
              <div className="flex justify-between text-neutral-400"><span>Success Rate:</span> <strong>{recovery.success_rate}%</strong></div>
            </>
          ) : (
            <div>Service Unreachable</div>
          )}
        </HealthCard>

        {/* Root Cause Incidents Card */}
        <HealthCard title="Root Cause Incidents" status={incidents && incidents.open_incidents > 0 ? "degraded" : "healthy"}>
          {incidents ? (
            <>
              <div className="flex justify-between"><span>Open Incidents:</span> <strong className="text-red-400">{incidents.open_incidents}</strong></div>
              <div className="flex justify-between"><span>Auto Resolved:</span> <strong className="text-green-400">{incidents.auto_resolved}</strong></div>
              <div className="flex justify-between"><span>Manual Intervention:</span> <strong className="text-yellow-400">{incidents.manual_intervention}</strong></div>
              <div className="flex justify-between border-t border-white/5 pt-2 mt-2"><span>Top Cause:</span> <strong className="truncate max-w-[120px] text-right" title={incidents.top_cause}>{incidents.top_cause}</strong></div>
              <div className="flex justify-between text-neutral-400"><span>Avg Confidence:</span> <strong>{incidents.average_confidence}</strong></div>
            </>
          ) : (
            <div>Service Unreachable</div>
          )}
        </HealthCard>

        {/* Latest AI Explanation Card */}
        <div className="p-6 rounded-xl border-2 border-neutral-700 bg-neutral-800/20 md:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold tracking-tight">Latest AI Explanation</h2>
            <div className="px-2 py-1 bg-purple-500/20 text-purple-400 text-xs rounded-md uppercase font-bold tracking-wider">
              AI Layer
            </div>
          </div>
          <div className="space-y-4 text-sm">
            {incidents?.latest_explanation ? (
              <>
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <div className="text-neutral-500 uppercase text-xs mb-1">Top Incident</div>
                        <div className="font-medium text-neutral-200">{incidents.latest_explanation.top_incident}</div>
                    </div>
                    <div>
                        <div className="text-neutral-500 uppercase text-xs mb-1">Confidence</div>
                        <div className="font-medium text-green-400">{incidents.latest_explanation.confidence}</div>
                    </div>
                </div>
                <div className="bg-black/20 p-4 rounded-lg border border-white/5">
                    <div className="text-neutral-500 uppercase text-xs mb-2">AI Summary</div>
                    <div className="text-neutral-300 leading-relaxed italic border-l-2 border-purple-500 pl-3">
                        {incidents.latest_explanation.ai_summary}
                    </div>
                </div>
              </>
            ) : (
              <div className="text-neutral-500 italic">No AI explanations available yet.</div>
            )}
          </div>
        </div>

        {/* Certification Status Card */}
        <div className="p-6 rounded-xl border-2 border-neutral-700 bg-neutral-800/20 md:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold tracking-tight">Continuous Certification</h2>
            {certification && certification.grade !== "N/A" && (
                <div className={`px-2 py-1 text-xs rounded-md uppercase font-bold tracking-wider ${
                    certification.grade.startsWith("A") ? "bg-green-500/20 text-green-400" :
                    certification.grade.startsWith("B") ? "bg-blue-500/20 text-blue-400" :
                    certification.grade.startsWith("C") ? "bg-yellow-500/20 text-yellow-400" :
                    "bg-red-500/20 text-red-400"
                }`}>
                  GRADE: {certification.grade}
                </div>
            )}
          </div>
          <div className="space-y-4 text-sm">
            {certification && certification.grade !== "N/A" ? (
              <>
                <div className="grid grid-cols-3 gap-4 mb-4 border-b border-white/5 pb-4">
                    <div>
                        <div className="text-neutral-500 uppercase text-xs mb-1">Last Run</div>
                        <div className="font-medium text-neutral-200">
                          {new Date(certification.last_run).toLocaleString()}
                        </div>
                    </div>
                    <div>
                        <div className="text-neutral-500 uppercase text-xs mb-1">Type</div>
                        <div className="font-medium text-neutral-200">{certification.type}</div>
                    </div>
                    <div>
                        <div className="text-neutral-500 uppercase text-xs mb-1">Pass Rate</div>
                        <div className={`font-medium ${certification.pass_rate === 100 ? "text-green-400" : "text-yellow-400"}`}>
                          {certification.pass_rate}%
                        </div>
                    </div>
                </div>
                
                <div className="text-neutral-500 uppercase text-xs mb-2">Recent Runs</div>
                <div className="space-y-2">
                    {certification.recent_runs.map((run, idx) => (
                        <div key={idx} className="flex items-center justify-between bg-black/20 p-2 rounded-md border border-white/5">
                            <div className="flex flex-col">
                                <span className="font-mono text-xs text-neutral-400">{run.run_id}</span>
                                <span className="text-xs text-neutral-500">{new Date(run.completed_at).toLocaleDateString()}</span>
                            </div>
                            <div className="flex space-x-4 text-xs">
                                <span className="uppercase text-neutral-400">{run.type}</span>
                                <span className="text-green-400">{run.passed} Pass</span>
                                <span className={run.failed > 0 ? "text-red-400" : "text-neutral-500"}>{run.failed} Fail</span>
                                <span className="font-bold w-6 text-right">{run.grade}</span>
                            </div>
                        </div>
                    ))}
                </div>
              </>
            ) : (
              <div className="text-neutral-500 italic">No certification runs recorded yet.</div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
