"use client";

import React, { useEffect, useState } from "react";
import { ShieldCheck, ArrowRight, Target, Activity, CheckCircle, Info } from "lucide-react";

export default function PolicyCenterPage() {
  const [pipeline, setPipeline] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPolicy, setSelectedPolicy] = useState<any>(null);

  useEffect(() => {
    // Stub for GET /admin/policies
    setTimeout(() => {
      setPipeline([
        {
          id: "pol_auth",
          name: "AuthenticationPolicy",
          order: 1,
          purpose: "Verifies valid enterprise identity",
          decisions: 1420
        },
        {
          id: "pol_budget",
          name: "BudgetPolicy",
          order: 2,
          purpose: "Enforces workspace cost limits",
          decisions: 1419
        },
        {
          id: "pol_visibility",
          name: "CapabilityVisibilityPolicy",
          order: 3,
          purpose: "Restricts capability access by visibility tier",
          decisions: 1419
        },
        {
          id: "pol_approval",
          name: "OptimizationApprovalPolicy",
          order: 4,
          purpose: "Blocks optimizations exceeding concurrency limits",
          decisions: 1419,
          failure_reason: "Concurrency exceeds policy limit",
          example_decisions: ["op_9f8e7d (APPROVED)", "op_blocked1 (REJECTED)"]
        }
      ]);
      setLoading(false);
    }, 500);
  }, []);

  return (
    <div className="flex flex-col h-full space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <ShieldCheck className="w-6 h-6 text-emerald-400" />
          Policy Center
        </h1>
        <p className="text-slate-400">Governance rules evaluated during execution.</p>
      </div>

      <div className="flex-1 flex gap-6 overflow-hidden">
        {/* Pipeline Tree (Left) */}
        <div className="flex-1 overflow-y-auto bg-slate-900 border border-slate-800 rounded-xl p-8 relative flex flex-col items-center">
          {loading ? (
            <div className="text-slate-500">Loading Policies...</div>
          ) : (
            <div className="flex flex-col items-center space-y-6 relative w-full max-w-lg">
              {/* Vertical line */}
              <div className="absolute top-0 left-1/2 w-0.5 h-full bg-slate-800 -translate-x-1/2 z-0"></div>

              {/* Source Goal */}
              <div className="bg-slate-950 border border-slate-700 rounded-lg p-3 w-64 text-center shadow-md relative z-10">
                <Target className="w-5 h-5 text-slate-500 mx-auto mb-1" />
                <h3 className="font-bold text-slate-300 text-sm">Goal Initialized</h3>
              </div>
              
              <ArrowRight className="w-5 h-5 text-slate-600 rotate-90 relative z-10 bg-slate-900" />

              {/* Policy Nodes */}
              {pipeline.map((policy) => (
                <React.Fragment key={policy.id}>
                  <button 
                    type="button"
                    onClick={() => setSelectedPolicy(policy)}
                    className="cursor-pointer bg-slate-950 border border-emerald-500/50 hover:border-emerald-400 rounded-lg p-4 w-72 text-center shadow-lg relative z-10 transition-colors block"
                  >
                    <ShieldCheck className="w-5 h-5 text-emerald-400 mx-auto mb-2" />
                    <h3 className="font-bold text-slate-200 text-sm">{policy.name}</h3>
                    <span className="block text-xs text-slate-500 mt-2 bg-slate-900 rounded py-1 border border-slate-800">
                      {policy.decisions} decisions
                    </span>
                  </button>
                  <ArrowRight className="w-5 h-5 text-slate-600 rotate-90 relative z-10 bg-slate-900" />
                </React.Fragment>
              ))}

              {/* Execution */}
              <div className="bg-slate-950 border border-slate-700 rounded-lg p-3 w-64 text-center shadow-md relative z-10">
                <Activity className="w-5 h-5 text-blue-500 mx-auto mb-1" />
                <h3 className="font-bold text-slate-300 text-sm">Execution</h3>
              </div>
            </div>
          )}
        </div>

        {/* Inspector Panel (Right) */}
        <div className="w-96 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col">
          <div className="p-4 border-b border-slate-800 bg-slate-800/30 flex items-center gap-2">
            <Info className="w-5 h-5 text-slate-400" />
            <h3 className="font-bold text-white">Policy Inspector</h3>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {selectedPolicy ? (
              <div className="space-y-6">
                <div>
                  <h4 className="text-lg font-bold text-white">{selectedPolicy.name}</h4>
                  <p className="text-sm text-slate-400 mt-1">{selectedPolicy.purpose}</p>
                </div>
                
                <div className="space-y-3">
                  <div className="flex justify-between items-center text-sm border-b border-slate-800 pb-2">
                    <span className="text-slate-500">Execution Order</span>
                    <span className="text-slate-200 font-mono">{selectedPolicy.order}</span>
                  </div>
                  <div className="flex justify-between items-center text-sm border-b border-slate-800 pb-2">
                    <span className="text-slate-500">Decisions Made</span>
                    <span className="text-slate-200 font-mono">{selectedPolicy.decisions}</span>
                  </div>
                  {selectedPolicy.failure_reason && (
                    <div className="flex justify-between items-center text-sm border-b border-slate-800 pb-2">
                      <span className="text-slate-500">Common Rejection</span>
                      <span className="text-rose-400 truncate max-w-[150px]" title={selectedPolicy.failure_reason}>
                        {selectedPolicy.failure_reason}
                      </span>
                    </div>
                  )}
                </div>

                {selectedPolicy.example_decisions && (
                  <div>
                    <h5 className="text-xs font-semibold text-slate-500 uppercase mb-2">Recent Decisions</h5>
                    <ul className="space-y-2">
                      {selectedPolicy.example_decisions.map((dec: string, i: number) => (
                        <li key={i} className="text-xs text-slate-300 bg-slate-950 p-2 rounded border border-slate-800 font-mono">
                          {dec}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                
                <div className="p-3 bg-blue-950/30 border border-blue-900/50 rounded-lg text-sm text-blue-200 flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                  <p>All policies trace back to deterministic Goal evaluation. Check Replay Explorer for specific evidence.</p>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500 text-sm text-center px-4">
                Select a policy in the pipeline to inspect its rules and decisions.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
