"use client";

import React, { useEffect, useState } from "react";
import { Target, Server, Shield, Box, GitMerge } from "lucide-react";

export default function GoalsPage() {
  const [goals, setGoals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Stub for GET /admin/goals
    setTimeout(() => {
      setGoals([
        {
          goal_id: "goal_1a2b3c",
          owner_id: "enterprise_service_account",
          state: "COMPLETED",
          description: "Action: trigger_research. Target: quantum_computing.",
          fingerprint: "abc123hash",
          created_at: "2026-06-14T10:00:01Z",
          workspace_id: "ws_998877"
        }
      ]);
      setLoading(false);
    }, 500);
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <Target className="w-6 h-6 text-blue-400" />
          Internal OS Goals
        </h1>
        <p className="text-slate-400">The core execution primitive. Tracing Goals reveals Planner branches, Agents, and Workspace state.</p>
      </div>

      <div className="grid gap-6">
        {loading ? (
          <div className="text-slate-400">Loading Goals...</div>
        ) : goals.map((goal) => (
          <div key={goal.goal_id} className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
            <div className="p-6 border-b border-slate-800 flex justify-between items-start bg-slate-800/30">
              <div>
                <h3 className="text-lg font-mono font-bold text-white flex items-center gap-2">
                  {goal.goal_id}
                  <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    {goal.state}
                  </span>
                </h3>
                <p className="text-slate-300 mt-2 text-sm">{goal.description}</p>
              </div>
              <div className="text-right text-xs text-slate-500 font-mono">
                Fingerprint: {goal.fingerprint}
              </div>
            </div>
            
            <div className="p-4 bg-slate-900 grid grid-cols-4 gap-4 divide-x divide-slate-800">
              <div className="px-4">
                <span className="flex items-center gap-2 text-slate-400 text-xs mb-1 uppercase tracking-wider">
                  <Shield className="w-3 h-3" /> Owner
                </span>
                <span className="text-slate-200 text-sm">{goal.owner_id}</span>
              </div>
              <div className="px-4">
                <span className="flex items-center gap-2 text-slate-400 text-xs mb-1 uppercase tracking-wider">
                  <Box className="w-3 h-3" /> Workspace
                </span>
                <span className="text-blue-400 font-mono text-sm hover:underline cursor-pointer">
                  {goal.workspace_id}
                </span>
              </div>
              <div className="px-4">
                <span className="flex items-center gap-2 text-slate-400 text-xs mb-1 uppercase tracking-wider">
                  <GitMerge className="w-3 h-3" /> Planner Trace
                </span>
                <span className="text-slate-200 text-sm">3 Branches Evaluated</span>
              </div>
              <div className="px-4">
                <span className="flex items-center gap-2 text-slate-400 text-xs mb-1 uppercase tracking-wider">
                  <Server className="w-3 h-3" /> Created
                </span>
                <span className="text-slate-200 text-sm">{new Date(goal.created_at).toLocaleString()}</span>
              </div>
            </div>
            
            <div className="p-3 bg-slate-950 border-t border-slate-800 flex justify-end">
              <button className="text-xs px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded font-medium transition-colors">
                Open in Replay Explorer
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
