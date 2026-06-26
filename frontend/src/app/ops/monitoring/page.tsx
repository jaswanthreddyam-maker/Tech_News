"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Activity, Clock, Zap, Target, RefreshCcw, ShieldAlert, BarChart, Server } from "lucide-react";

// --- EventService Abstraction ---
// This isolates the UI from transport mechanics (ADR-0084).
// In the future, this can easily switch to WebSockets without changing the component layer.
class EventService {
  static async fetchEvents() {
    // Stub: Simulate API call to /admin/monitoring/events
    return new Promise<any[]>((resolve) => {
      setTimeout(() => {
        resolve([
          { id: `evt_${Date.now()}_1`, timestamp: new Date().toISOString(), event: "Circuit Half Open", severity: "WARNING", target: "ContentExtraction", link: "/ops/capabilities" },
          { id: `evt_${Date.now()}_2`, timestamp: new Date(Date.now() - 5000).toISOString(), event: "Reflection Finished", severity: "INFO", target: "Goal_1a2b3c", link: "/ops/replay/goal_1a2b3c" },
          { id: `evt_${Date.now()}_3`, timestamp: new Date(Date.now() - 10000).toISOString(), event: "Artifact Published", severity: "SUCCESS", target: "art_112233", link: "/ops/artifacts" },
          { id: `evt_${Date.now()}_4`, timestamp: new Date(Date.now() - 15000).toISOString(), event: "Goal Completed", severity: "SUCCESS", target: "Goal_1a2b3c", link: "/ops/replay/goal_1a2b3c" }
        ]);
      }, 300);
    });
  }
}

export default function MonitoringPage() {
  const [scheduler, setScheduler] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Initial load of structural data
  useEffect(() => {
    setTimeout(() => {
      setScheduler({
        queues: {
          planning: { depth: 3, status: "HEALTHY" },
          execution: { depth: 18, status: "HEALTHY" },
          reflection: { depth: 4, status: "HEALTHY" },
          evaluation: { depth: 2, status: "HEALTHY" }
        },
        capabilities: [
          { capability: "WebSearch", latency_ms: 320, availability: 99.9, failure_rate: 0.01, circuit_state: "CLOSED", timeout_ms: 5000, last_failure: null, version: "v2" },
          { capability: "ContentExtraction", latency_ms: 1250, availability: 98.5, failure_rate: 0.05, circuit_state: "HALF_OPEN", timeout_ms: 15000, last_failure: "2026-06-14T09:15:00Z", version: "v1" }
        ],
        recent_incidents: [
          { type: "Capability Timeout", time: "2026-06-14T09:15:00Z", target: "ContentExtraction" },
          { type: "Lease Expired", time: "2026-06-14T09:18:00Z", target: "Agent_Worker_2" },
          { type: "Planner Retry", time: "2026-06-14T09:21:00Z", target: "Goal_1a2b3c" }
        ]
      });
      setLoading(false);
    }, 500);
  }, []);

  // Polling abstraction for Live Events
  useEffect(() => {
    let isMounted = true;
    
    const pollEvents = async () => {
      try {
        const newEvents = await EventService.fetchEvents();
        if (isMounted) setEvents(newEvents);
      } catch (err) {
        console.error("Event fetch failed", err);
      }
    };

    pollEvents(); // Initial fetch
    const intervalId = setInterval(pollEvents, 5000); // 5s polling

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, []);

  const getSeverityStyle = (severity: string) => {
    switch(severity) {
      case "INFO": return "text-blue-400 bg-blue-500/10 border-blue-500/20";
      case "WARNING": return "text-amber-400 bg-amber-500/10 border-amber-500/20";
      case "ERROR": return "text-rose-400 bg-rose-500/10 border-rose-500/20";
      case "SUCCESS": return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
      default: return "text-slate-400 bg-slate-800 border-slate-700";
    }
  };

  const getCircuitStyle = (state: string) => {
    switch(state) {
      case "CLOSED": return "text-emerald-400";
      case "HALF_OPEN": return "text-amber-400";
      case "OPEN": return "text-rose-400";
      default: return "text-slate-400";
    }
  };

  if (loading) return <div className="text-slate-400 p-6">Loading Runtime Telemetry...</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <BarChart className="w-6 h-6 text-indigo-400" />
          Monitoring Dashboard
        </h1>
        <p className="text-slate-400">Live operational telemetry across the AIOS runtime.</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Left Column: Scheduler & Queues */}
        <div className="space-y-6">
          {/* Scheduler Summary */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 bg-slate-800/30">
              <h2 className="font-bold text-white flex items-center gap-2">
                <RefreshCcw className="w-4 h-4 text-indigo-400" /> Scheduler
              </h2>
            </div>
            <div className="p-4 grid grid-cols-2 gap-4">
              <div>
                <span className="block text-xs text-slate-500 uppercase">Running</span>
                <span className="text-xl font-bold text-emerald-400">14</span>
              </div>
              <div>
                <span className="block text-xs text-slate-500 uppercase">Waiting</span>
                <span className="text-xl font-bold text-slate-300">12</span>
              </div>
              <div>
                <span className="block text-xs text-slate-500 uppercase">Retries</span>
                <span className="text-xl font-bold text-amber-400">1</span>
              </div>
              <div>
                <span className="block text-xs text-slate-500 uppercase">Dead Letters</span>
                <span className="text-xl font-bold text-slate-500">0</span>
              </div>
            </div>
          </div>

          {/* Queue Health */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 bg-slate-800/30">
              <h2 className="font-bold text-white flex items-center gap-2">
                <Server className="w-4 h-4 text-purple-400" /> Queue Health
              </h2>
            </div>
            <div className="p-4 space-y-4">
              {Object.entries(scheduler.queues).map(([name, data]: [string, any]) => (
                <div key={name} className="flex justify-between items-center">
                  <span className="text-sm font-medium text-slate-300 capitalize">{name} Queue</span>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-mono text-white">{data.depth} msg</span>
                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Incidents */}
          <div className="bg-slate-900 border border-rose-900/30 rounded-xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 bg-rose-950/20">
              <h2 className="font-bold text-rose-400 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4" /> Recent Incidents
              </h2>
            </div>
            <div className="p-4 space-y-3">
              {scheduler.recent_incidents.map((inc: any, i: number) => (
                <div key={i} className="text-sm border-l-2 border-rose-500 pl-3 py-1">
                  <div className="text-slate-300 font-medium">{inc.type}</div>
                  <div className="text-xs text-slate-500 flex justify-between mt-1">
                    <span className="font-mono text-blue-400">{inc.target}</span>
                    <span>{new Date(inc.time).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Middle Column: Capability Health */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden xl:col-span-1">
          <div className="p-4 border-b border-slate-800 bg-slate-800/30">
            <h2 className="font-bold text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" /> Capability Health
            </h2>
          </div>
          <div className="p-4 space-y-6">
            {scheduler.capabilities.map((cap: any) => (
              <div key={cap.capability} className="p-4 rounded-lg border border-slate-800 bg-slate-950">
                <div className="flex justify-between items-start mb-3">
                  <Link href="/ops/capabilities" className="font-bold text-blue-400 hover:underline">{cap.capability}</Link>
                  <span className={`text-xs font-bold ${getCircuitStyle(cap.circuit_state)}`}>
                    {cap.circuit_state}
                  </span>
                </div>
                
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div>
                    <span className="block text-[10px] text-slate-500 uppercase">Availability</span>
                    <span className="text-sm text-white">{cap.availability}%</span>
                  </div>
                  <div>
                    <span className="block text-[10px] text-slate-500 uppercase">Avg Latency</span>
                    <span className="text-sm text-white">{cap.latency_ms}ms</span>
                  </div>
                  <div>
                    <span className="block text-[10px] text-slate-500 uppercase">Failure Rate</span>
                    <span className="text-sm text-white">{(cap.failure_rate * 100).toFixed(1)}%</span>
                  </div>
                  <div>
                    <span className="block text-[10px] text-slate-500 uppercase">Timeout Limit</span>
                    <span className="text-sm text-slate-400">{cap.timeout_ms}ms</span>
                  </div>
                </div>

                <div className="flex justify-between items-center text-xs pt-3 border-t border-slate-800">
                  <span className="text-slate-500">Version: <span className="text-slate-300 font-mono">{cap.version}</span></span>
                  {cap.last_failure && (
                    <span className="text-rose-400">Fail: {new Date(cap.last_failure).toLocaleTimeString()}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Live Events Stream */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden xl:col-span-1 flex flex-col h-[800px]">
          <div className="p-4 border-b border-slate-800 bg-slate-800/30 flex justify-between items-center">
            <h2 className="font-bold text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-400" /> Live Events
            </h2>
            <div className="flex items-center gap-1.5 px-2 py-0.5 bg-slate-950 border border-slate-800 rounded text-xs text-slate-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> Polling
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {events.length === 0 ? (
              <div className="text-center text-slate-500 text-sm mt-4">Waiting for events...</div>
            ) : (
              events.map((evt) => (
                <div key={evt.id} className="p-3 rounded-lg border border-slate-800 bg-slate-950 hover:bg-slate-900 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${getSeverityStyle(evt.severity)}`}>
                      {evt.severity}
                    </span>
                    <span className="text-xs text-slate-500 flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {new Date(evt.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="text-sm font-bold text-white mb-1">{evt.event}</div>
                  <Link 
                    href={evt.link} 
                    className="text-xs font-mono text-blue-400 hover:text-blue-300 hover:underline flex items-center gap-1 mt-2 inline-flex"
                  >
                    <Target className="w-3 h-3" /> {evt.target}
                  </Link>
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
