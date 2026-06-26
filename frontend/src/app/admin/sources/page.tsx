/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../../../services/api";
import {
  Radio,
  Play,
  ToggleLeft,
  ToggleRight,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { EmptyState, EmptyIllustration } from "@/components/common/EmptyState";

interface Source {
  id: number;
  name: string;
  category: string;
  method: string;
  url: string;
  credibility_score: number;
  crawl_interval: number;
  enabled: boolean;
  health_state: string;
  total_crawls: number;
  successful_crawls: number;
  reliability_score: number;
  last_crawl_at: string | null;
  is_deleted: boolean;
  created_at: string;
}

export default function AdminSourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<number | null>(null);
  const [triggeringId, setTriggeringId] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  // Soft Delete & Restore State
  const [showDeleted, setShowDeleted] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  // Edit Modal State
  const [editingSource, setEditingSource] = useState<Source | null>(null);
  const [editName, setEditName] = useState("");
  const [editUrl, setEditUrl] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [editCredibility, setEditCredibility] = useState(50);
  const [editInterval, setEditInterval] = useState(3600);
  const [savingEdit, setSavingEdit] = useState(false);

  const fetchSources = async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    else setRefreshing(true);
    try {
      const data = await apiFetch<Source[]>("/admin/sources", {
        params: { show_deleted: showDeleted ? "true" : "false" },
      });
      setSources(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load sources registry.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchSources();
  }, [showDeleted]);

  const handleToggle = async (id: number) => {
    setTogglingId(id);
    setMessage(null);
    try {
      const res: any = await apiFetch(`/admin/sources/${id}/toggle`, {
        method: "POST",
      });
      setSources((prev) =>
        (Array.isArray(prev) ? prev : []).map((s) => (s.id === id ? { ...s, enabled: res.enabled } : s))
      );
      setMessage(res.message);
    } catch (err: any) {
      setError(err.message || "Failed to update source active state.");
    } finally {
      setTogglingId(null);
    }
  };

  const handleTrigger = async (id: number) => {
    setTriggeringId(id);
    setMessage(null);
    try {
      const res: any = await apiFetch(`/admin/sources/${id}/trigger`, {
        method: "POST",
      });
      setMessage(res.message);
      fetchSources(true);
    } catch (err: any) {
      setError(err.message || "Scraping session failed or timed out.");
    } finally {
      setTriggeringId(null);
    }
  };

  const handleEditOpen = (s: Source) => {
    setEditingSource(s);
    setEditName(s.name);
    setEditUrl(s.url);
    setEditCategory(s.category);
    setEditCredibility(s.credibility_score);
    setEditInterval(s.crawl_interval);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingSource) return;
    setSavingEdit(true);
    setMessage(null);
    try {
      const res: any = await apiFetch(`/admin/sources/${editingSource.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: editName,
          url: editUrl,
          category: editCategory,
          credibility_score: Number(editCredibility),
          crawl_interval: Number(editInterval),
        }),
      });
      setMessage(res.message);
      setEditingSource(null);
      fetchSources(true);
    } catch (err: any) {
      setError(err.message || "Failed to update source configuration.");
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to soft-delete this news source?")) return;
    setDeletingId(id);
    setMessage(null);
    try {
      const res: any = await apiFetch(`/admin/sources/${id}`, {
        method: "DELETE",
      });
      setMessage(res.message);
      fetchSources(true);
    } catch (err: any) {
      setError(err.message || "Failed to soft-delete source.");
    } finally {
      setDeletingId(null);
    }
  };

  const handleRestore = async (id: number) => {
    setDeletingId(id);
    setMessage(null);
    try {
      const res: any = await apiFetch(`/admin/sources/${id}/restore`, {
        method: "POST",
      });
      setMessage(res.message);
      fetchSources(true);
    } catch (err: any) {
      setError(err.message || "Failed to restore source.");
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 font-mono text-[11px]">
        <div className="flex items-center justify-between">
          <div className="h-4 bg-neutral-900 w-48 animate-pulse" />
        </div>
        <div className="border border-[#1a1a1a] bg-black p-4 space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-8 bg-neutral-950 animate-pulse w-full border-b border-[#111]" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Radio className="w-3.5 h-3.5 text-[#888]" />
          <h1 className="font-mono text-[11px] tracking-widest uppercase text-white font-bold">
            NEWSROOM SOURCES REGISTRY
          </h1>
        </div>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer select-none font-mono text-[9px] tracking-widest uppercase text-[#888] hover:text-white transition-colors">
            <input
              type="checkbox"
              checked={showDeleted}
              onChange={(e) => setShowDeleted(e.target.checked)}
              className="accent-white cursor-pointer"
            />
            SHOW DELETED
          </label>
          <button
            onClick={() => fetchSources(true)}
            disabled={refreshing}
            className="flex items-center gap-1.5 font-mono text-[9px] tracking-widest uppercase text-[#888] hover:text-white transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${refreshing ? "animate-spin" : ""}`} />
            REFRESH
          </button>
        </div>
      </div>

      {/* Message & Error banners */}
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

      {/* Main Table */}
      <div className="border border-[#1a1a1a] bg-black overflow-x-auto">
        <table className="w-full text-left font-mono text-[11px]">
          <thead>
            <tr className="border-b border-[#1a1a1a] bg-[#0c0c0c] text-[#555] select-none text-[9px]">
              <th className="p-3">ID</th>
              <th className="p-3">SOURCE NAME</th>
              <th className="p-3">METHOD</th>
              <th className="p-3">CATEGORY</th>
              <th className="p-3">RELIABILITY</th>
              <th className="p-3">HEALTH</th>
              <th className="p-3">STATUS</th>
              <th className="p-3 text-right">ACTIONS</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#111]">
            {sources.map((s) => (
              <tr key={s.id} className={`hover:bg-[#060606] transition-colors ${s.is_deleted ? "opacity-45" : ""}`}>
                <td className="p-3 text-[#555]">{s.id}</td>
                <td className="p-3 font-semibold text-[#ccc]">
                  <div>{s.name}</div>
                  <div className="text-[9px] text-[#555] truncate max-w-[250px]">{s.url}</div>
                </td>
                <td className="p-3 text-[#888] uppercase">{s.method}</td>
                <td className="p-3 text-[#888]">{s.category}</td>
                <td className="p-3">
                  <span
                    className={
                      s.reliability_score >= 80
                        ? "text-emerald-400"
                        : s.reliability_score >= 50
                        ? "text-amber-400"
                        : "text-red-400"
                    }
                  >
                    {s.reliability_score}%
                  </span>
                </td>
                <td className="p-3">
                  <span
                    className={`inline-flex items-center px-1.5 py-0.5 text-[8px] font-bold tracking-wider uppercase border ${
                      s.health_state === "healthy"
                        ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-400"
                        : s.health_state === "degraded"
                        ? "border-amber-500/20 bg-amber-500/5 text-amber-400"
                        : "border-red-500/20 bg-red-500/5 text-red-400"
                    }`}
                  >
                    {s.health_state}
                  </span>
                </td>
                <td className="p-3">
                  <button
                    onClick={() => handleToggle(s.id)}
                    disabled={togglingId !== null || s.is_deleted}
                    className="flex items-center gap-1.5 focus:outline-none disabled:opacity-50"
                  >
                    {s.enabled ? (
                      <ToggleRight className="w-5 h-5 text-emerald-400" />
                    ) : (
                      <ToggleLeft className="w-5 h-5 text-[#333]" />
                    )}
                  </button>
                </td>
                <td className="p-3 text-right">
                  <div className="inline-flex gap-1.5">
                    {s.is_deleted ? (
                      <button
                        onClick={() => handleRestore(s.id)}
                        disabled={deletingId !== null}
                        className="font-mono text-[9px] font-bold tracking-wider uppercase bg-emerald-500 text-black px-2.5 py-1 hover:bg-emerald-400 transition-colors"
                      >
                        RESTORE
                      </button>
                    ) : (
                      <>
                        <button
                          onClick={() => handleTrigger(s.id)}
                          disabled={triggeringId !== null || !s.enabled}
                          className="inline-flex items-center gap-1 font-mono text-[9px] tracking-wider uppercase bg-foreground text-background px-2.5 py-1 hover:bg-neutral-300 disabled:opacity-30 disabled:hover:bg-foreground transition-colors"
                        >
                          <Play className="w-2.5 h-2.5 fill-current" />
                          CRAWL
                        </button>
                        <button
                          onClick={() => handleEditOpen(s)}
                          className="font-mono text-[9px] tracking-wider uppercase border border-[#333] hover:border-[#555] px-2.5 py-1 text-[#ccc] hover:text-white transition-colors"
                        >
                          EDIT
                        </button>
                        <button
                          onClick={() => handleDelete(s.id)}
                          disabled={deletingId !== null}
                          className="font-mono text-[9px] tracking-wider uppercase bg-red-950/40 hover:bg-red-950 text-red-400 border border-red-950/60 px-2.5 py-1 transition-colors disabled:opacity-30"
                        >
                          DELETE
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {sources.length === 0 && (
              <tr>
                <td colSpan={8} className="p-8">
                  <EmptyState size="sm">
                    <EmptyIllustration
                      icon={Radio}
                      title="No sources found"
                      description="No sources match active registry filters."
                    />
                  </EmptyState>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Edit Modal */}
      {editingSource && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="w-full max-w-md bg-[#0c0c0c] border border-[#1a1a1a] p-6 space-y-4">
            <div className="border-b border-[#1a1a1a] pb-2 flex items-center justify-between">
              <h2 className="font-mono text-[10px] tracking-widest uppercase text-white font-bold">
                EDIT CRAWLER SOURCE #{editingSource.id}
              </h2>
              <span className="font-mono text-[8px] text-[#555] uppercase">
                {editingSource.method}
              </span>
            </div>
            <form onSubmit={handleEditSubmit} className="space-y-4 font-mono text-[11px]">
              <div>
                <label htmlFor="edit-name" className="block text-[#555] text-[9px] tracking-wider uppercase mb-1">SOURCE NAME</label>
                <input
                  id="edit-name"
                  type="text"
                  required
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full bg-[#080808] border border-[#1a1a1a] px-2.5 py-2 text-white focus:outline-none focus:border-white transition-colors"
                />
              </div>
              <div>
                <label htmlFor="edit-url" className="block text-[#555] text-[9px] tracking-wider uppercase mb-1">ENDPOINT URL</label>
                <input
                  id="edit-url"
                  type="url"
                  required
                  value={editUrl}
                  onChange={(e) => setEditUrl(e.target.value)}
                  className="w-full bg-[#080808] border border-[#1a1a1a] px-2.5 py-2 text-white focus:outline-none focus:border-white transition-colors"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label htmlFor="edit-category" className="block text-[#555] text-[9px] tracking-wider uppercase mb-1">CATEGORY</label>
                  <select
                    id="edit-category"
                    value={editCategory}
                    onChange={(e) => setEditCategory(e.target.value)}
                    className="w-full bg-[#080808] border border-[#1a1a1a] px-2 py-2 text-[#ccc] focus:outline-none focus:border-white transition-colors"
                  >
                    <option value="official">official</option>
                    <option value="editorial">editorial</option>
                    <option value="community">community</option>
                    <option value="social">social</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="edit-credibility" className="block text-[#555] text-[9px] tracking-wider uppercase mb-1">CREDIBILITY (0-100)</label>
                  <input
                    id="edit-credibility"
                    type="number"
                    min="0"
                    max="100"
                    required
                    value={editCredibility}
                    onChange={(e) => setEditCredibility(Number(e.target.value))}
                    className="w-full bg-[#080808] border border-[#1a1a1a] px-2.5 py-2 text-white focus:outline-none focus:border-white transition-colors"
                  />
                </div>
              </div>
              <div>
                <label htmlFor="edit-interval" className="block text-[#555] text-[9px] tracking-wider uppercase mb-1">CRAWL INTERVAL (SECONDS)</label>
                <input
                  id="edit-interval"
                  type="number"
                  min="60"
                  required
                  value={editInterval}
                  onChange={(e) => setEditInterval(Number(e.target.value))}
                  className="w-full bg-[#080808] border border-[#1a1a1a] px-2.5 py-2 text-white focus:outline-none focus:border-white transition-colors"
                />
              </div>
              <div className="flex justify-end gap-2 pt-3 border-t border-[#1a1a1a]">
                <button
                  type="button"
                  onClick={() => setEditingSource(null)}
                  className="border border-[#333] text-[#ccc] hover:text-white px-4 py-2 uppercase text-[9px] tracking-wider transition-colors"
                >
                  CANCEL
                </button>
                <button
                  type="submit"
                  disabled={savingEdit}
                  className="bg-white text-black hover:bg-neutral-200 px-4 py-2 uppercase text-[9px] font-bold tracking-wider disabled:opacity-50 transition-colors"
                >
                  {savingEdit ? "SAVING..." : "SAVE CHANGES"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
