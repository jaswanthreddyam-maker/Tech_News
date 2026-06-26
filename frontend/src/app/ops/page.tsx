"use client";

import React, { useEffect, useState } from "react";
import { Activity, Server, Clock, ShieldCheck, Box, Target, RefreshCcw, Archive } from "lucide-react";
import Link from "next/link";

export default function OpsOverviewPage() {
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Stub for GET /admin/health
    setTimeout(() => {
      setHealth({
        platform: { status: "HEALTHY", version: "v1.0", configuration: "v18", capabilities: "42/42" },
        scheduler: { queue_depth: 27, running_goals: 14, waiting_goals: 12, retries: 1, dead_letters: 0 },
        execution: { average_latency_ms: 420, artifacts_today: 1247, replay_success_rate: 99.8, planner_success_rate: 98.5 },
        governance: { pending_approvals: 3, published_config: "v18", rejected_configs: 2, policy_violations: 1 }
      });
      setLoading(false);
    }, 500);
  }, []);

  if (loading) return <div className="text-slate-400 p-6">Loading Platform Health...</div>;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
          <Activity className="w-8 h-8 text-blue-400" />
          Platform Health
        </h1>
        <p className="text-slate-400 mt-1">The operational homepage of AIOS. Real-time telemetry across the entire execution platform.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Platform Group */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-blue-400 border-b border-slate-800 pb-2">
            <Server className="w-5 h-5" />
            <h2 className="text-lg font-bold">Platform</h2>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-xs text-slate-500 uppercase font-semibold">Overall Health</span>
              <div className="mt-1 flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div>
                <span className="text-xl font-bold text-white">{health.platform.status}</span>
              </div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-xs text-slate-500 uppercase font-semibold">Capabilities</span>
              <div className="mt-1 text-xl font-bold text-white">{health.platform.capabilities} Available</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-xs text-slate-500 uppercase font-semibold">OS Version</span>
              <div className="mt-1 text-lg font-mono text-slate-300">{health.platform.version}</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 cursor-pointer hover:border-slate-600 transition-colors">
              <span className="text-xs text-slate-500 uppercase font-semibold">Configuration</span>
              <Link href="/ops/configuration" className="block mt-1 text-lg font-mono text-blue-400 hover:underline">
                {health.platform.configuration}
              </Link>
            </div>
          </div>
        </div>

        {/* Scheduler Group */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-indigo-400 border-b border-slate-800 pb-2">
            <RefreshCcw className="w-5 h-5" />
            <h2 className="text-lg font-bold">Scheduler</h2>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex justify-between items-end">
              <div>
                <span className="text-xs text-slate-500 uppercase font-semibold">Queue Depth</span>
                <div className="mt-1 text-2xl font-bold text-white">{health.scheduler.queue_depth}</div>
              </div>
              <Link href="/ops/monitoring" className="text-xs text-indigo-400 hover:underline">View Queues</Link>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-xs text-slate-500 uppercase font-semibold">Running Goals</span>
              <div className="mt-1 text-2xl font-bold text-emerald-400">{health.scheduler.running_goals}</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-xs text-slate-500 uppercase font-semibold">Waiting Goals</span>
              <div className="mt-1 text-xl font-bold text-slate-300">{health.scheduler.waiting_goals}</div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-center">
                <span className="text-[10px] text-slate-500 uppercase font-semibold">Retries</span>
                <span className="text-lg font-bold text-amber-400">{health.scheduler.retries}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-center">
                <span className="text-[10px] text-slate-500 uppercase font-semibold">Dead Letters</span>
                <span className={`text-lg font-bold ${health.scheduler.dead_letters > 0 ? 'text-rose-500' : 'text-slate-500'}`}>
                  {health.scheduler.dead_letters}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Execution Group */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-emerald-400 border-b border-slate-800 pb-2">
            <Target className="w-5 h-5" />
            <h2 className="text-lg font-bold">Execution</h2>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-xs text-slate-500 uppercase font-semibold">Average Latency</span>
              <div className="mt-1 text-2xl font-bold text-white flex items-baseline gap-1">
                {health.execution.average_latency_ms} <span className="text-sm font-normal text-slate-500">ms</span>
              </div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex justify-between items-end">
              <div>
                <span className="text-xs text-slate-500 uppercase font-semibold">Artifacts Today</span>
                <div className="mt-1 text-2xl font-bold text-white">{health.execution.artifacts_today}</div>
              </div>
              <Link href="/ops/artifacts" className="text-xs text-emerald-400 hover:underline">Browse</Link>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-xs text-slate-500 uppercase font-semibold">Replay Success</span>
              <div className="mt-1 text-xl font-bold text-emerald-400">{health.execution.replay_success_rate}%</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-xs text-slate-500 uppercase font-semibold">Planner Success</span>
              <div className="mt-1 text-xl font-bold text-emerald-400">{health.execution.planner_success_rate}%</div>
            </div>
          </div>
        </div>

        {/* Governance Group */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-amber-400 border-b border-slate-800 pb-2">
            <ShieldCheck className="w-5 h-5" />
            <h2 className="text-lg font-bold">Governance</h2>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30">
              <span className="text-xs text-amber-500/70 uppercase font-semibold">Pending Approvals</span>
              <div className="mt-1 text-2xl font-bold text-amber-400">{health.governance.pending_approvals}</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-xs text-slate-500 uppercase font-semibold">Published Config</span>
              <div className="mt-1 text-lg font-mono text-slate-300">{health.governance.published_config}</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-xs text-slate-500 uppercase font-semibold">Rejected Configs</span>
              <div className="mt-1 text-xl font-bold text-slate-400">{health.governance.rejected_configs}</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex justify-between items-end">
              <div>
                <span className="text-xs text-slate-500 uppercase font-semibold">Policy Violations</span>
                <div className={`mt-1 text-xl font-bold ${health.governance.policy_violations > 0 ? 'text-amber-500' : 'text-slate-400'}`}>
                  {health.governance.policy_violations}
                </div>
              </div>
              <Link href="/ops/policies" className="text-xs text-amber-400 hover:underline">Investigate</Link>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
