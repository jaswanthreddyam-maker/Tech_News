"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../../../services/api";
import { ToggleLeft, ToggleRight, AlertCircle, RefreshCw, Sliders } from "lucide-react";

interface FeatureFlag {
  id: number;
  name: string;
  enabled: boolean;
  description: string;
  updated_at: string;
}

export default function AdminFlagsPage() {
  const [flags, setFlags] = useState<FeatureFlag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [togglingName, setTogglingName] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const fetchFlags = async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    else setRefreshing(true);
    try {
      const data = await apiFetch<FeatureFlag[]>("/admin/feature-flags");
      setFlags(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load active system feature flags.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchFlags();
  }, []);

  const handleToggle = async (name: string, currentEnabled: boolean) => {
    setTogglingName(name);
    setMessage(null);
    try {
      const targetEnabled = !currentEnabled;
      const res: any = await apiFetch(`/admin/feature-flags/${name}/toggle`, {
        method: "POST",
        body: JSON.stringify({ enabled: targetEnabled }),
      });
      setFlags((prev) =>
        (Array.isArray(prev) ? prev : []).map((f) => (f.name === name ? { ...f, enabled: res.enabled } : f))
      );
      setMessage(res.message);
    } catch (err: any) {
      setError(err.message || "Failed to toggle feature flag.");
    } finally {
      setTogglingName(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 font-mono text-[11px]">
        <div className="h-4 bg-neutral-900 w-48 animate-pulse" />
        <div className="border border-[#1a1a1a] bg-black p-4 space-y-4 animate-pulse">
          <div className="h-10 bg-neutral-950 w-full" />
          <div className="h-10 bg-neutral-950 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sliders className="w-3.5 h-3.5 text-[#888]" />
          <h1 className="font-mono text-[11px] tracking-widest uppercase text-white font-bold">
            SYSTEM PARAMETERS & FEATURE FLAGS
          </h1>
        </div>
        <button
          onClick={() => fetchFlags(true)}
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

      {/* Flags list */}
      <div className="border border-[#1a1a1a] bg-black overflow-x-auto">
        <table className="w-full text-left font-mono text-[11px]">
          <thead>
            <tr className="border-b border-[#1a1a1a] bg-[#0c0c0c] text-[#555] select-none text-[9px]">
              <th className="p-3">FLAG IDENTIFIER</th>
              <th className="p-3">DESCRIPTION / INTENT</th>
              <th className="p-3">UPDATED</th>
              <th className="p-3 text-right">TOGGLE STATE</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#111]">
            {flags.map((f) => (
              <tr key={f.id} className="hover:bg-[#060606] transition-colors leading-relaxed">
                <td className="p-3 text-white font-semibold">{f.name}</td>
                <td className="p-3 text-[#888] max-w-[300px]">{f.description}</td>
                <td className="p-3 text-[#555]">{new Date(f.updated_at).toLocaleString()}</td>
                <td className="p-3 text-right">
                  <button
                    onClick={() => handleToggle(f.name, f.enabled)}
                    disabled={togglingName !== null}
                    className="inline-flex items-center gap-1.5 focus:outline-none disabled:opacity-50"
                  >
                    {f.enabled ? (
                      <ToggleRight className="w-5 h-5 text-emerald-400" />
                    ) : (
                      <ToggleLeft className="w-5 h-5 text-[#333]" />
                    )}
                  </button>
                </td>
              </tr>
            ))}
            {flags.length === 0 && (
              <tr>
                <td colSpan={4} className="p-8 text-center text-[#555]">
                  No operational feature flags configured.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
