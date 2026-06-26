"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { PlaySquare, Target, Clock, ArrowRight } from "lucide-react";

export default function ReplayIndexPage() {
  const [replays, setReplays] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Stub: fetch recent completed goals available for replay
    setTimeout(() => {
      setReplays([
        {
          goal_id: "goal_1a2b3c",
          operation_id: "op_9f8e7d",
          description: "Action: trigger_research. Target: quantum_computing.",
          created_at: "2026-06-14T10:00:00Z",
          duration_ms: 18200,
          score: 92
        }
      ]);
      setLoading(false);
    }, 500);
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <PlaySquare className="w-6 h-6 text-blue-400" />
          Replay Explorer
        </h1>
        <p className="text-slate-400">Deterministic execution debugger. Trace any past execution through its exact planner branches, capabilities, and artifacts.</p>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-800/50 text-slate-300 border-b border-slate-800">
            <tr>
              <th className="px-6 py-4 font-medium">Goal ID</th>
              <th className="px-6 py-4 font-medium">Description</th>
              <th className="px-6 py-4 font-medium">Duration</th>
              <th className="px-6 py-4 font-medium">Eval Score</th>
              <th className="px-6 py-4 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {loading ? (
              <tr><td colSpan={5} className="px-6 py-4 text-center text-slate-500">Loading...</td></tr>
            ) : replays.map((r) => (
              <tr key={r.goal_id} className="hover:bg-slate-800/50 transition-colors">
                <td className="px-6 py-4 font-mono text-slate-300 flex items-center gap-2">
                  <Target className="w-4 h-4 text-slate-500" />
                  {r.goal_id}
                </td>
                <td className="px-6 py-4 text-slate-400 truncate max-w-xs">{r.description}</td>
                <td className="px-6 py-4 text-slate-400 flex items-center gap-1">
                  <Clock className="w-3 h-3" /> {(r.duration_ms / 1000).toFixed(1)}s
                </td>
                <td className="px-6 py-4">
                  <span className="px-2 py-1 rounded bg-emerald-500/10 text-emerald-400 font-bold border border-emerald-500/20">
                    {r.score}/100
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <Link 
                    href={`/ops/replay/${r.goal_id}`}
                    className="inline-flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded font-medium transition-colors"
                  >
                    Launch Replay <ArrowRight className="w-4 h-4" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
