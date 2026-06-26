/* eslint-disable @typescript-eslint/no-unused-vars */
"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../../../services/api";
import { ShieldAlert, AlertCircle, RefreshCw, Radio } from "lucide-react";

export default function AdminEmergencyPage() {
  const [cutoffActive, setCutoffActive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [acting, setActing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const fetchSwitch = async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    else setRefreshing(true);
    try {
      const res: any = await apiFetch("/admin/emergency-switch");
      setCutoffActive(res.cutoff_active);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to retrieve emergency cutoff configuration.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchSwitch();
  }, []);

  const handleToggle = async (targetState: boolean) => {
    setActing(true);
    setMessage(null);
    try {
      const res: any = await apiFetch("/admin/emergency-switch/toggle", {
        method: "POST",
        body: JSON.stringify({ state: targetState }),
      });
      setCutoffActive(res.cutoff_active);
      setMessage(res.message);
    } catch (err: any) {
      setError(err.message || "Failed to update emergency cutoff state.");
    } finally {
      setActing(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 font-mono text-[11px]">
        <div className="h-4 bg-neutral-900 w-48 animate-pulse" />
        <div className="border border-red-500/10 bg-red-500/5 p-8 h-48 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-3.5 h-3.5 text-red-500" />
          <h1 className="font-mono text-[11px] tracking-widest uppercase text-white font-bold">
            GLOBAL EMERGENCY CUTOFF
          </h1>
        </div>
        <button
          onClick={() => fetchSwitch(true)}
          disabled={refreshing}
          className="flex items-center gap-1.5 font-mono text-[9px] tracking-widest uppercase text-[#888] hover:text-white transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${refreshing ? "animate-spin" : ""}`} />
          REFRESH
        </button>
      </div>

      {/* banners */}
      {error && (
        <div className="border border-red-500/30 bg-red-500/5 px-3 py-2 flex items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
          <p className="font-mono text-[10px] text-red-400">{error}</p>
        </div>
      )}

      {message && (
        <div className="border border-emerald-500/30 bg-emerald-500/5 px-3 py-2">
          <p className="font-mono text-[10px] text-emerald-400">{message}</p>
        </div>
      )}

      {/* Main warning control block */}
      <div className="border border-red-500/30 bg-black/60 p-6 space-y-6">
        <div className="space-y-2">
          <h3 className="font-mono text-xs font-bold text-red-400 tracking-wider uppercase">
            GLOBAL PIPELINE CUTOFF CONTROLLER
          </h3>
          <p className="font-sans text-[11px] text-[#888] leading-relaxed">
            Activating the global cutoff immediately halts all background crawl engines, Redis
            scraping queue workers, and AI ingestion scripts. Use this control in case of scraper malfunctions, rate-limit bans, or database maintenance cycles.
          </p>
        </div>

        <div className="border-t border-[#1a1a1a] pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span
              className={`h-3 w-3 shrink-0 rounded-full ${
                cutoffActive ? "bg-red-500 animate-pulse" : "bg-emerald-500"
              }`}
            />
            <span className="font-mono text-xs font-bold text-white tracking-widest uppercase">
              CUTOFF STATUS: {cutoffActive ? "ACTIVE (PIPELINE STOPPED)" : "INACTIVE (RUNNING)"}
            </span>
          </div>

          <button
            onClick={() => handleToggle(!cutoffActive)}
            disabled={acting}
            className={`font-mono text-[10px] tracking-widest uppercase font-bold px-4 py-2 hover:bg-neutral-300 transition-all ${
              cutoffActive
                ? "bg-emerald-500 text-black hover:bg-emerald-400"
                : "bg-red-500 text-black hover:bg-red-400"
            } disabled:opacity-50`}
          >
            {acting
              ? "EXECUTING SHUTDOWN..."
              : cutoffActive
              ? "RESUME INGESTION ENGINE"
              : "CUTOFF ALL ENGINES"}
          </button>
        </div>
      </div>
    </div>
  );
}
