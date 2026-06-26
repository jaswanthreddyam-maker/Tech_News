"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../../../services/api";
import { TrendingUp, RefreshCw, AlertCircle } from "lucide-react";

interface Trend {
  topic: string;
  weight: number;
}

export default function AdminTrendsPage() {
  const [trends, setTrends] = useState<Trend[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchTrends = async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    else setRefreshing(true);
    try {
      const data: any = await apiFetch("/telemetry");
      if (data && Array.isArray(data.trending_spikes)) {
        setTrends(data.trending_spikes);
      } else {
        setTrends([]);
      }
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load trending topics telemetry.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchTrends();
  }, []);

  if (loading) {
    return (
      <div className="space-y-4 font-mono text-[11px]">
        <div className="flex items-center justify-between">
          <div className="h-4 bg-neutral-900 w-48 animate-pulse" />
        </div>
        <div className="border border-[#1a1a1a] bg-black p-4 space-y-4">
          <div className="h-8 bg-neutral-950 animate-pulse w-full" />
          <div className="h-8 bg-neutral-950 animate-pulse w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-3.5 h-3.5 text-[#888]" />
          <h1 className="font-mono text-[11px] tracking-widest uppercase text-white font-bold">
            EMERGING TECHNOLOGY TRENDS
          </h1>
        </div>
        <button
          onClick={() => fetchTrends(true)}
          disabled={refreshing}
          className="flex items-center gap-1.5 font-mono text-[9px] tracking-widest uppercase text-[#888] hover:text-white transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${refreshing ? "animate-spin" : ""}`} />
          REFRESH
        </button>
      </div>

      {error && (
        <div className="border border-red-500/30 bg-red-500/5 px-3 py-2 flex items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
          <p className="font-mono text-[10px] text-red-400">{error}</p>
        </div>
      )}

      {/* Grid Display of Trending Topics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="border border-[#1a1a1a] bg-black p-4">
          <h3 className="font-mono text-[9px] tracking-widest uppercase text-[#888] font-bold mb-3">
            TOP DISCOVERED KEYWORDS
          </h3>
          <div className="space-y-1">
            {trends.map((t, idx) => (
              <div
                key={t.topic}
                className="flex items-center justify-between border-b border-[#111] py-2 font-mono text-[11px]"
              >
                <div className="flex items-center gap-2">
                  <span className="text-[#555]">#{idx + 1}</span>
                  <span className="text-white font-semibold">{t.topic}</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-24 bg-neutral-900 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-emerald-500 h-full"
                      style={{ width: `${Math.min(100, t.weight * 10)}%` }}
                    />
                  </div>
                  <span className="text-emerald-400 font-bold">{t.weight.toFixed(1)}</span>
                </div>
              </div>
            ))}
            {trends.length === 0 && (
              <p className="text-[#555] p-4 text-center">No active trends computed.</p>
            )}
          </div>
        </div>

        <div className="border border-[#1a1a1a] bg-[#0c0c0c] p-4 flex flex-col justify-between">
          <div>
            <h3 className="font-mono text-[9px] tracking-widest uppercase text-[#888] font-bold mb-2">
              TREND SCORING AGENT LOGIC
            </h3>
            <p className="font-sans text-[11px] text-[#ccc] leading-relaxed">
              The platform&apos;s autonomous trends extraction engine processes incoming crawl content
              and ranks topics using custom term-frequency / document-frequency (TF-IDF) spikes. High
              scoring topics automatically prioritize downstream generation.
            </p>
          </div>
          <div className="mt-4 border-t border-[#1a1a1a] pt-3 flex items-center justify-between">
            <span className="font-mono text-[8px] text-[#555] tracking-widest uppercase">
              AGENT STATE: SLEEPING
            </span>
            <span className="font-mono text-[8px] text-emerald-400 tracking-widest uppercase">
              CYCLE INTERVAL: 1H
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
