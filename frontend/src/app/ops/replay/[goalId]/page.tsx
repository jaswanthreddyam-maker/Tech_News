"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Target, Server, Briefcase, Zap, Archive, FlaskConical, ChevronRight, Activity, Cpu } from "lucide-react";

type TraceNode = { type: string; title: string; subtitle?: string; data: any };

export default function ReplayTracePage() {
  const params = useParams();
  const goalId = params.goalId as string;
  
  const [trace, setTrace] = useState<any>(null);
  const [selectedNode, setSelectedNode] = useState<TraceNode | null>(null);

  useEffect(() => {
    // Stub for GET /admin/replay/{goal_id}
    setTimeout(() => {
      setTrace({
        metadata: { goal_id: goalId, operation_id: "op_9f8e7d", duration_ms: 18200 },
        planner: { strategy: "react", latency_ms: 1200, branches: ["branch_a", "branch_b"] },
        workspace: { initial_snapshot: "ws_100", final_snapshot: "ws_105" },
        branches: [
          { branch_id: "branch_a", name: "Research Path", tasks: ["task_1"] },
          { branch_id: "branch_b", name: "Comparison Path", tasks: ["task_2"] }
        ],
        tasks: [
          { task_id: "task_1", capability: "Research", status: "COMPLETED" },
          { task_id: "task_2", capability: "Comparison", status: "COMPLETED" }
        ],
        capabilities: [
          { capability: "Research", latency_ms: 4500 },
          { capability: "Comparison", latency_ms: 3200 }
        ],
        artifacts: [
          { artifact_id: "art_112233", type: "research_report", status: "PUBLISHED" }
        ],
        reflection: { approved: true, reasoning: "All evidence compiled successfully." },
        evaluation: { score: 92, human_feedback: "Accepted", configuration_version: "v17" }
      });
    }, 500);
  }, [goalId]);

  if (!trace) return <div className="text-slate-400 p-6">Loading execution trace...</div>;

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 text-sm text-slate-500 font-medium">
        <Link href="/ops/operations" className="hover:text-slate-300">Operation {trace.metadata.operation_id}</Link>
        <ChevronRight className="w-4 h-4" />
        <Link href="/ops/goals" className="hover:text-slate-300">Goal {trace.metadata.goal_id}</Link>
        <ChevronRight className="w-4 h-4" />
        <span className="text-white">Replay</span>
      </div>

      {/* Execution Outcome Panel */}
      <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-6 flex justify-between items-center">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            Execution Outcome <span className="text-emerald-400 text-sm bg-emerald-500/10 px-2 py-0.5 rounded">SUCCESS</span>
          </h2>
          <div className="flex gap-6 mt-3 text-sm text-slate-300">
            <div><span className="text-slate-500 block text-xs">Evaluation Score</span> <span className="font-bold text-white">{trace.evaluation.score}/100</span></div>
            <div><span className="text-slate-500 block text-xs">Human Feedback</span> <span className="font-bold text-white">{trace.evaluation.human_feedback}</span></div>
            <div><span className="text-slate-500 block text-xs">Duration</span> <span className="font-bold text-white">{(trace.metadata.duration_ms / 1000).toFixed(1)}s</span></div>
            <div><span className="text-slate-500 block text-xs">Config Version</span> <span className="font-bold text-blue-400">{trace.evaluation.configuration_version}</span></div>
          </div>
        </div>
        <div className="text-right">
          <FlaskConical className="w-12 h-12 text-emerald-500/50" />
        </div>
      </div>

      <div className="flex-1 flex gap-6 overflow-hidden">
        {/* Execution Tree (Left Pane) */}
        <div className="flex-1 overflow-y-auto bg-slate-900 border border-slate-800 rounded-xl p-8 relative">
          <div className="absolute top-0 left-1/2 w-0.5 h-full bg-slate-800 -translate-x-1/2 z-0"></div>
          
          <div className="flex flex-col items-center space-y-12 relative z-10">
            {/* Goal Node */}
            <button type="button" onClick={() => setSelectedNode({ type: "Goal", title: goalId, data: trace.metadata })} className="cursor-pointer bg-slate-950 border border-blue-500/50 rounded-lg p-4 w-64 text-center shadow-lg hover:border-blue-400 transition-colors block">
              <Target className="w-6 h-6 text-blue-400 mx-auto mb-2" />
              <h3 className="font-bold text-slate-200">Goal Dispatched</h3>
            </button>

            {/* Planner Node */}
            <button type="button" onClick={() => setSelectedNode({ type: "Planner", title: "React Planner", subtitle: `Latency: ${trace.planner.latency_ms}ms`, data: trace.planner })} className="cursor-pointer bg-slate-950 border border-slate-700 rounded-lg p-4 w-64 text-center shadow-lg hover:border-slate-500 transition-colors block">
              <Server className="w-6 h-6 text-slate-400 mx-auto mb-2" />
              <h3 className="font-bold text-slate-200">Planning & Strategy</h3>
              <p className="text-xs text-slate-500 mt-1">{trace.planner.strategy.toUpperCase()}</p>
            </button>

            {/* Workspace Node */}
            <button type="button" onClick={() => setSelectedNode({ type: "Workspace", title: trace.workspace.initial_snapshot, data: trace.workspace })} className="cursor-pointer bg-slate-950 border border-purple-500/50 rounded-lg p-4 w-64 text-center shadow-lg hover:border-purple-400 transition-colors block">
              <Briefcase className="w-6 h-6 text-purple-400 mx-auto mb-2" />
              <h3 className="font-bold text-slate-200">Workspace Snapshot</h3>
            </button>

            {/* Branches (Parallel Flex Layout) */}
            <div className="flex justify-center gap-16 w-full relative">
              {/* Horizontal connecting line */}
              <div className="absolute top-0 left-1/4 right-1/4 h-0.5 bg-slate-800 z-0"></div>
              
              {trace.branches.map((branch: any, idx: number) => (
                <div key={branch.branch_id} className="flex flex-col items-center space-y-8 relative z-10 pt-4">
                  {/* Vertical branch line */}
                  <div className="absolute top-0 left-1/2 w-0.5 h-full bg-slate-800 -translate-x-1/2 z-0"></div>
                  
                  <div className="bg-slate-800 px-3 py-1 rounded-full text-xs font-bold text-slate-300 relative z-10 border border-slate-700">
                    {branch.name}
                  </div>
                  
                  {branch.tasks.map((taskId: string) => {
                    const task = trace.tasks.find((t: any) => t.task_id === taskId);
                    const cap = trace.capabilities.find((c: any) => c.capability === task.capability);
                    return (
                      <button type="button" key={taskId} onClick={() => setSelectedNode({ type: "Capability", title: task.capability, data: { task, capability: cap } })} className="cursor-pointer bg-slate-950 border border-amber-500/50 rounded-lg p-4 w-48 text-center shadow-lg relative z-10 hover:border-amber-400 transition-colors block">
                        <Zap className="w-5 h-5 text-amber-400 mx-auto mb-2" />
                        <h3 className="font-bold text-slate-200 text-sm">{task.capability}</h3>
                        <p className="text-xs text-slate-500 mt-1">{cap.latency_ms}ms</p>
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>

            {/* Artifacts Node */}
            <button type="button" onClick={() => setSelectedNode({ type: "Artifacts", title: "Published Outputs", data: trace.artifacts })} className="cursor-pointer bg-slate-950 border border-indigo-500/50 rounded-lg p-4 w-64 text-center shadow-lg hover:border-indigo-400 transition-colors block">
              <Archive className="w-6 h-6 text-indigo-400 mx-auto mb-2" />
              <h3 className="font-bold text-slate-200">Artifact Published</h3>
              <p className="text-xs text-slate-500 mt-1">{trace.artifacts[0].artifact_id}</p>
            </button>
            
            {/* Reflection Node */}
            <button type="button" onClick={() => setSelectedNode({ type: "Reflection", title: "System Reflection", data: trace.reflection })} className="cursor-pointer bg-slate-950 border border-teal-500/50 rounded-lg p-4 w-64 text-center shadow-lg hover:border-teal-400 transition-colors block">
              <Activity className="w-6 h-6 text-teal-400 mx-auto mb-2" />
              <h3 className="font-bold text-slate-200">Reflection</h3>
              <p className="text-xs text-teal-500 mt-1">{trace.reflection.approved ? "APPROVED" : "REJECTED"}</p>
            </button>
          </div>
        </div>

        {/* Inspector Panel (Right Pane) */}
        <div className="w-80 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col">
          <div className="p-4 border-b border-slate-800 bg-slate-800/30 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-slate-400" />
            <h3 className="font-bold text-white">Inspector</h3>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {selectedNode ? (
              <div className="space-y-4">
                <div>
                  <span className="text-xs font-bold text-blue-400 uppercase tracking-wider">{selectedNode.type}</span>
                  <h4 className="text-lg font-bold text-white mt-1">{selectedNode.title}</h4>
                  {selectedNode.subtitle && <p className="text-sm text-slate-400">{selectedNode.subtitle}</p>}
                </div>
                
                <div className="border-t border-slate-800 pt-4">
                  <h5 className="text-xs font-semibold text-slate-500 uppercase mb-2">Payload Details</h5>
                  <pre className="bg-slate-950 p-3 rounded-md text-xs text-emerald-400 overflow-x-auto border border-slate-800">
                    {JSON.stringify(selectedNode.data, null, 2)}
                  </pre>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500 text-sm text-center px-4">
                Select any node in the execution tree to inspect its payload, latency, and status.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
