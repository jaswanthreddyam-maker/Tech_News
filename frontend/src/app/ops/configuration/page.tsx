"use client";

import React, { useEffect, useState } from "react";
import { Settings, GitCommit, Search, Plus, ArrowRight, Target, ShieldCheck, Archive } from "lucide-react";

export default function ConfigurationCenterPage() {
  const [configs, setConfigs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("ALL");
  const [activeTab, setActiveTab] = useState("diff");

  // Selected config defaults to the pending one for diffing
  const [selectedConfig, setSelectedConfig] = useState<any>(null);
  // Published config is the baseline
  const [publishedConfig, setPublishedConfig] = useState<any>(null);

  useEffect(() => {
    // Stub for GET /admin/configurations
    setTimeout(() => {
      const data = [
        {
          version: "v10",
          status: "PENDING_APPROVAL",
          author: "admin_user_123",
          source_operation: "op_new_config",
          created_at: "2026-06-14T12:00:00Z",
          payload: {
            max_agent_concurrency: 24,
            planner_timeout_ms: 8000,
            reflection_enabled: true,
            lease_ttl: 600
          }
        },
        {
          version: "v9",
          status: "PUBLISHED",
          author: "system",
          source_operation: "op_baseline",
          created_at: "2026-06-01T00:00:00Z",
          payload: {
            max_agent_concurrency: 16,
            planner_timeout_ms: 10000,
            reflection_enabled: false,
            lease_ttl: 600
          }
        },
        {
          version: "v8",
          status: "SUPERSEDED",
          author: "system",
          source_operation: "op_init",
          created_at: "2026-05-15T00:00:00Z",
          payload: {
            max_agent_concurrency: 8,
            planner_timeout_ms: 15000,
            reflection_enabled: false,
            lease_ttl: 600
          }
        }
      ];
      setConfigs(data);
      const active = data.find(c => c.status === "PUBLISHED");
      const pending = data.find(c => c.status === "PENDING_APPROVAL") || active;
      setPublishedConfig(active);
      setSelectedConfig(pending);
      setLoading(false);
    }, 500);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "PUBLISHED": return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
      case "PENDING_APPROVAL": return "text-amber-400 bg-amber-500/10 border-amber-500/20";
      case "REJECTED": return "text-rose-400 bg-rose-500/10 border-rose-500/20";
      case "SUPERSEDED": return "text-slate-400 bg-slate-500/10 border-slate-500/20";
      default: return "text-slate-400 bg-slate-800";
    }
  };

  const filteredConfigs = configs.filter(c => filter === "ALL" || c.status === filter);

  return (
    <div className="flex flex-col h-full space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Settings className="w-6 h-6 text-indigo-400" />
            Configuration Center
          </h1>
          <p className="text-slate-400">Versioned history of the platform&apos;s system_configuration artifact.</p>
        </div>

        {/* Mutation Pipeline Visualization Stub */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-3 flex items-center gap-3">
          <span className="text-xs font-semibold text-slate-500 uppercase">Mutation Flow:</span>
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="px-2 py-1 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center gap-1">
              <Plus className="w-3 h-3" /> Intent
            </span>
            <ArrowRight className="w-3 h-3 text-slate-600" />
            <span className="flex items-center gap-1"><Target className="w-3 h-3" /> Goal</span>
            <ArrowRight className="w-3 h-3 text-slate-600" />
            <span className="flex items-center gap-1"><ShieldCheck className="w-3 h-3" /> Approval</span>
            <ArrowRight className="w-3 h-3 text-slate-600" />
            <span className="flex items-center gap-1"><Archive className="w-3 h-3" /> Published</span>
          </div>
        </div>
      </div>

      <div className="flex-1 flex gap-6 overflow-hidden">
        {/* Left Panel: Timeline */}
        <div className="w-80 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col">
          <div className="p-4 border-b border-slate-800 bg-slate-800/30 space-y-4">
            <h3 className="font-bold text-white flex items-center gap-2">
              <GitCommit className="w-5 h-5 text-slate-400" />
              Timeline
            </h3>
            <div className="flex gap-2 text-xs">
              {["ALL", "PUBLISHED", "PENDING_APPROVAL"].map(f => (
                <button 
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-2 py-1 rounded border transition-colors ${filter === f ? 'bg-indigo-500/20 border-indigo-500/30 text-indigo-300' : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-300'}`}
                >
                  {f === "PENDING_APPROVAL" ? "PENDING" : f}
                </button>
              ))}
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {loading ? <div className="text-slate-500">Loading...</div> : filteredConfigs.map(c => (
              <button 
                key={c.version}
                type="button"
                onClick={() => setSelectedConfig(c)}
                className={`w-full text-left p-3 rounded-lg border cursor-pointer transition-colors block ${selectedConfig?.version === c.version ? 'bg-slate-800 border-indigo-500/50' : 'bg-slate-950 border-slate-800 hover:border-slate-700'}`}
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="font-bold text-white">{c.version}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded border font-semibold ${getStatusColor(c.status)}`}>
                    {c.status.replace("_", " ")}
                  </span>
                </div>
                <div className="text-xs text-slate-500 flex justify-between">
                  <span>{new Date(c.created_at).toLocaleDateString()}</span>
                  <span className="font-mono">{c.author}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Right Panel: Diff / Overview */}
        <div className="flex-1 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col">
          <div className="p-4 border-b border-slate-800 bg-slate-800/30 flex justify-between items-center">
            <div className="flex gap-4">
              {["overview", "diff", "raw"].map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`text-sm font-medium pb-1 border-b-2 transition-colors ${activeTab === tab ? 'text-white border-indigo-400' : 'text-slate-400 border-transparent hover:text-slate-300'}`}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>
            {selectedConfig && (
              <span className="text-sm font-mono text-slate-400">
                Viewing {selectedConfig.version}
              </span>
            )}
          </div>
          
          <div className="flex-1 overflow-y-auto p-6 bg-slate-950">
            {loading || !selectedConfig ? (
              <div className="text-slate-500">Loading details...</div>
            ) : activeTab === "overview" ? (
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="block text-xs text-slate-500 uppercase mb-1">Status</span>
                    <span className={`text-sm font-bold ${getStatusColor(selectedConfig.status).split(' ')[0]}`}>
                      {selectedConfig.status}
                    </span>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="block text-xs text-slate-500 uppercase mb-1">Author</span>
                    <span className="text-sm text-slate-200">{selectedConfig.author}</span>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="block text-xs text-slate-500 uppercase mb-1">Created At</span>
                    <span className="text-sm text-slate-200">{new Date(selectedConfig.created_at).toLocaleString()}</span>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="block text-xs text-slate-500 uppercase mb-1">Source Operation</span>
                    <span className="text-sm font-mono text-blue-400">{selectedConfig.source_operation}</span>
                  </div>
                </div>
              </div>
            ) : activeTab === "raw" ? (
              <pre className="text-emerald-400 text-sm font-mono p-4 bg-slate-900 rounded-lg border border-slate-800">
                {JSON.stringify(selectedConfig.payload, null, 2)}
              </pre>
            ) : (
              // Diff View
              <div className="space-y-4">
                <div className="flex items-center gap-3 text-sm text-slate-400 mb-6 bg-slate-900 p-3 rounded-lg border border-slate-800">
                  <span className="font-mono text-white bg-slate-800 px-2 py-1 rounded">{publishedConfig?.version} (Published)</span>
                  <ArrowRight className="w-4 h-4" />
                  <span className="font-mono text-white bg-slate-800 px-2 py-1 rounded">{selectedConfig.version} ({selectedConfig.status})</span>
                </div>
                
                {/* Manual diff mock for demonstration of ADR-0083 implementation */}
                <div className="font-mono text-sm space-y-1 bg-slate-900 border border-slate-800 p-4 rounded-lg">
                  {Object.keys(selectedConfig.payload).map(key => {
                    const pubVal = publishedConfig?.payload[key];
                    const selVal = selectedConfig.payload[key];
                    
                    if (pubVal === selVal) {
                      return (
                        <div key={key} className="text-slate-500 grid grid-cols-12 py-1">
                          <span className="col-span-1 text-center"> </span>
                          <span className="col-span-4">{key}</span>
                          <span className="col-span-7">{String(selVal)}</span>
                        </div>
                      );
                    } else if (pubVal !== undefined && selVal !== undefined) {
                      return (
                        <div key={key} className="flex flex-col py-1 border-y border-slate-800/50 my-1 bg-slate-950/50">
                          <div className="text-rose-400 grid grid-cols-12 bg-rose-950/20">
                            <span className="col-span-1 text-center font-bold">-</span>
                            <span className="col-span-4">{key}</span>
                            <span className="col-span-7">{String(pubVal)}</span>
                          </div>
                          <div className="text-emerald-400 grid grid-cols-12 bg-emerald-950/20">
                            <span className="col-span-1 text-center font-bold">+</span>
                            <span className="col-span-4">{key}</span>
                            <span className="col-span-7">{String(selVal)}</span>
                          </div>
                        </div>
                      );
                    }
                    return null;
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
