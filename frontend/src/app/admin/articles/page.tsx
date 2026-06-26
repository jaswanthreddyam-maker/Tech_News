"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../../../services/api";
import {
  FileText,
  Check,
  X,
  FileCode,
  AlertCircle,
  RefreshCw,
  Edit,
  History,
} from "lucide-react";
import { EmptyState, EmptyIllustration } from "@/components/common/EmptyState";

interface PendingArticle {
  id: number;
  title: string;
  slug: string;
  summary: string;
  content: string;
  tags: string | null;
  source_name: string;
  ai_confidence: number;
  published_status: string;
  created_at: string;
}

export default function AdminArticlesPage() {
  const [articles, setArticles] = useState<PendingArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [moderatingId, setModeratingId] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  // Edit Modal & Revisions state
  const [editingArticle, setEditingArticle] = useState<PendingArticle | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editSummary, setEditSummary] = useState("");
  const [editTags, setEditTags] = useState("");
  const [revisions, setRevisions] = useState<any[]>([]);
  const [loadingRevisions, setLoadingRevisions] = useState(false);
  const [revisionError, setRevisionError] = useState<string | null>(null);
  const [savingEdit, setSavingEdit] = useState(false);
  const [rollingBackId, setRollingBackId] = useState<number | null>(null);

  const fetchPendingArticles = async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    else setRefreshing(true);
    try {
      const data = await apiFetch<PendingArticle[]>("/admin/articles/pending");
      setArticles(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load pending moderation articles queue.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchPendingArticles();
  }, []);

  const handleModerate = async (id: number, action: "publish" | "reject" | "draft") => {
    setModeratingId(id);
    setMessage(null);
    try {
      const res: any = await apiFetch(`/admin/articles/${id}/moderate`, {
        method: "POST",
        body: JSON.stringify({ action }),
      });
      setArticles((prev) => (Array.isArray(prev) ? prev : []).filter((a) => a.id !== id));
      setMessage(res.message);
    } catch (err: any) {
      setError(err.message || "Moderation action failed.");
    } finally {
      setModeratingId(null);
    }
  };

  const fetchRevisions = async (articleId: number) => {
    try {
      setLoadingRevisions(true);
      const res = await apiFetch<any[]>(`/admin/articles/${articleId}/revisions`);
      setRevisions(Array.isArray(res) ? res : []);
      setRevisionError(null);
    } catch (err: any) {
      setRevisionError(err.message || "Failed to load revisions.");
    } finally {
      setLoadingRevisions(false);
    }
  };

  const openEditModal = (article: PendingArticle) => {
    setEditingArticle(article);
    setEditTitle(article.title);
    setEditSummary(article.summary);
    setEditTags(article.tags || "");
    setRevisions([]);
    setRevisionError(null);
    fetchRevisions(article.id);
  };

  const handleSaveEdit = async () => {
    if (!editingArticle) return;
    setSavingEdit(true);
    setError(null);
    setMessage(null);
    try {
      const res: any = await apiFetch(`/admin/articles/${editingArticle.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          title: editTitle,
          summary: editSummary,
          tags: editTags,
        }),
      });
      setArticles((prev) =>
        (Array.isArray(prev) ? prev : []).map((a) =>
          a.id === editingArticle.id
            ? { ...a, title: editTitle, summary: editSummary, tags: editTags }
            : a
        )
      );
      setMessage(res.message);
      setEditingArticle(null);
    } catch (err: any) {
      setError(err.message || "Failed to save article updates.");
    } finally {
      setSavingEdit(false);
    }
  };

  const handleRollback = async (revisionNumber: number) => {
    if (!editingArticle) return;
    setRollingBackId(revisionNumber);
    setError(null);
    setMessage(null);
    try {
      const res: any = await apiFetch(`/admin/articles/${editingArticle.id}/rollback/${revisionNumber}`, {
        method: "POST",
      });
      await fetchPendingArticles(true);
      setMessage(res.message);
      setEditingArticle(null);
    } catch (err: any) {
      setError(err.message || "Rollback failed.");
    } finally {
      setRollingBackId(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 font-mono text-[11px]">
        <div className="flex items-center justify-between">
          <div className="h-4 bg-neutral-900 w-48 animate-pulse" />
        </div>
        <div className="border border-[#1a1a1a] bg-black p-4 space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-neutral-950 animate-pulse w-full border-b border-[#111]" />
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
          <FileText className="w-3.5 h-3.5 text-[#888]" />
          <h1 className="font-mono text-[11px] tracking-widest uppercase text-white font-bold">
            EDITORIAL MODERATION DESK
          </h1>
        </div>
        <button
          onClick={() => fetchPendingArticles(true)}
          disabled={refreshing}
          className="flex items-center gap-1.5 font-mono text-[9px] tracking-widest uppercase text-[#888] hover:text-white transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${refreshing ? "animate-spin" : ""}`} />
          REFRESH
        </button>
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

      {/* Pending queue table */}
      <div className="border border-[#1a1a1a] bg-black overflow-x-auto">
        <table className="w-full text-left font-mono text-[11px]">
          <caption className="sr-only">Pending Articles Queue</caption>
          <thead>
            <tr className="border-b border-[#1a1a1a] bg-[#0c0c0c] text-[#555] select-none text-[9px]">
              <th scope="col" className="p-3">ID</th>
              <th scope="col" className="p-3">ARTICLE TITLE & SUMMARY</th>
              <th scope="col" className="p-3">SOURCE</th>
              <th scope="col" className="p-3">AI VALUE</th>
              <th scope="col" className="p-3">STAGE</th>
              <th scope="col" className="p-3 text-right">MODERATE</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#111]">
            {articles.map((a) => (
              <tr key={a.id} className="hover:bg-[#060606] transition-colors">
                <td className="p-3 text-[#555]">{a.id}</td>
                <td className="p-3 max-w-[400px]">
                  <div className="font-semibold text-[#ccc] leading-normal">{a.title}</div>
                  <div className="text-[10px] text-[#555] line-clamp-2 mt-1 leading-relaxed">
                    {a.summary}
                  </div>
                </td>
                <td className="p-3 text-[#888]">{a.source_name}</td>
                <td className="p-3">
                  <span
                    className={
                      a.ai_confidence >= 90
                        ? "text-emerald-400"
                        : a.ai_confidence >= 75
                        ? "text-amber-400"
                        : "text-red-400"
                    }
                  >
                    {a.ai_confidence}%
                  </span>
                </td>
                <td className="p-3">
                  <span className="inline-flex items-center px-1.5 py-0.5 text-[8px] font-bold tracking-wider uppercase border border-amber-500/20 bg-amber-500/5 text-amber-400">
                    {a.published_status}
                  </span>
                </td>
                <td className="p-3 text-right">
                  <div className="inline-flex gap-1.5">
                    <button
                      onClick={() => openEditModal(a)}
                      disabled={moderatingId !== null}
                      title="Edit article details and revisions"
                      className="bg-sky-600 text-white px-2 py-1 font-mono text-[9px] font-bold uppercase tracking-wider hover:bg-sky-500 disabled:opacity-30 transition-colors"
                    >
                      <Edit className="w-3 h-3" />
                    </button>
                    <button
                      onClick={() => handleModerate(a.id, "publish")}
                      disabled={moderatingId !== null}
                      title="Approve and Publish story"
                      className="bg-emerald-500 text-black px-2 py-1 font-mono text-[9px] font-bold uppercase tracking-wider hover:bg-emerald-400 disabled:opacity-30 transition-colors"
                    >
                      <Check className="w-3 h-3" />
                    </button>
                    <button
                      onClick={() => handleModerate(a.id, "reject")}
                      disabled={moderatingId !== null}
                      title="Reject and archive story"
                      className="bg-red-500 text-black px-2 py-1 font-mono text-[9px] font-bold uppercase tracking-wider hover:bg-red-400 disabled:opacity-30 transition-colors"
                    >
                      <X className="w-3 h-3" />
                    </button>
                    <button
                      onClick={() => handleModerate(a.id, "draft")}
                      disabled={moderatingId !== null}
                      title="Keep as Draft"
                      className="bg-neutral-800 text-[#ccc] border border-[#333] px-2 py-1 font-mono text-[9px] font-bold uppercase tracking-wider hover:bg-neutral-700 disabled:opacity-30 transition-colors"
                    >
                      <FileCode className="w-3 h-3" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {articles.length === 0 && (
              <tr>
                <td colSpan={6} className="p-8">
                  <EmptyState size="sm">
                    <EmptyIllustration
                      icon={FileText}
                      title="No pending approvals"
                      description="No stories waiting in moderation review queue."
                    />
                  </EmptyState>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Edit & Revisions Modal */}
      {editingArticle && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
          <div className="w-full max-w-3xl border border-[#1a1a1a] bg-black p-6 font-mono text-[11px] space-y-4 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-[#1a1a1a] pb-3">
              <div className="flex items-center gap-2">
                <Edit className="w-3.5 h-3.5 text-sky-400" />
                <span className="font-bold text-white tracking-widest uppercase">
                  EDIT ARTICLE DETAILS & HISTORICAL REVISIONS
                </span>
              </div>
              <button
                onClick={() => setEditingArticle(null)}
                className="text-[#555] hover:text-white transition-colors"
              >
                [CLOSE]
              </button>
            </div>

            {/* Edit Fields */}
            <div className="space-y-3">
              <div className="flex flex-col gap-1">
                <label htmlFor="edit-title" className="text-[#555] uppercase text-[9px] tracking-wider font-semibold">
                  Title
                </label>
                <input
                  id="edit-title"
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="bg-[#050505] border border-[#1a1a1a] px-3 py-2 text-white focus:outline-none focus:border-white transition-colors"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label htmlFor="edit-summary" className="text-[#555] uppercase text-[9px] tracking-wider font-semibold">
                  Summary
                </label>
                <textarea
                  id="edit-summary"
                  rows={3}
                  value={editSummary}
                  onChange={(e) => setEditSummary(e.target.value)}
                  className="bg-[#050505] border border-[#1a1a1a] px-3 py-2 text-white focus:outline-none focus:border-white transition-colors resize-y leading-relaxed"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label htmlFor="edit-tags" className="text-[#555] uppercase text-[9px] tracking-wider font-semibold">
                  Tags (Comma Separated)
                </label>
                <input
                  id="edit-tags"
                  type="text"
                  value={editTags}
                  onChange={(e) => setEditTags(e.target.value)}
                  placeholder="e.g. ai, coding, tech"
                  className="bg-[#050505] border border-[#1a1a1a] px-3 py-2 text-white focus:outline-none focus:border-white transition-colors"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-b border-[#1a1a1a] pb-4">
                <button
                  onClick={() => setEditingArticle(null)}
                  className="border border-[#1a1a1a] px-4 py-2 hover:bg-neutral-900 transition-colors text-[#888] font-bold"
                >
                  CANCEL
                </button>
                <button
                  onClick={handleSaveEdit}
                  disabled={savingEdit}
                  className="bg-sky-600 hover:bg-sky-500 text-white font-bold px-5 py-2 disabled:opacity-40 transition-colors"
                >
                  {savingEdit ? "SAVING..." : "SAVE CHANGES"}
                </button>
              </div>
            </div>

            {/* Revisions Section */}
            <div className="space-y-3 pt-2">
              <div className="flex items-center gap-1.5 text-[#555]">
                <History className="w-3.5 h-3.5" />
                <span className="font-bold uppercase text-[9px] tracking-widest">
                  REVISION HISTORY & REVERSAL LOG
                </span>
              </div>

              {loadingRevisions ? (
                <div className="py-4 text-center text-[#555] animate-pulse">
                  LOADING HISTORICAL SNAPSHOTS...
                </div>
              ) : revisionError ? (
                <div className="text-red-400 text-[10px]">{revisionError}</div>
              ) : revisions.length === 0 ? (
                <div className="text-[#555] text-[10px]">
                  No revisions captured yet for this story. Revisions are created on every edit.
                </div>
              ) : (
                <div className="border border-[#1a1a1a] max-h-48 overflow-y-auto">
                  <table className="w-full text-left font-mono text-[10px]">
                    <caption className="sr-only">Revision History</caption>
                    <thead>
                      <tr className="bg-[#0c0c0c] border-b border-[#1a1a1a] text-[#555] text-[8px] uppercase select-none">
                        <th scope="col" className="p-2">REV #</th>
                        <th scope="col" className="p-2">TIMESTAMP</th>
                        <th scope="col" className="p-2">OPERATOR</th>
                        <th scope="col" className="p-2">TITLE AT REVISION</th>
                        <th scope="col" className="p-2 text-right">ACTION</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#111]">
                      {revisions.map((r) => (
                        <tr key={r.id} className="hover:bg-[#050505] transition-colors">
                          <td className="p-2 text-sky-400 font-bold">#{r.revision_number}</td>
                          <td className="p-2 text-[#555]">
                            {new Date(r.created_at).toLocaleString()}
                          </td>
                          <td className="p-2 text-[#888] truncate max-w-[120px]" title={r.user_email}>
                            {r.user_email}
                          </td>
                          <td className="p-2 text-[#ccc] truncate max-w-[200px]" title={r.title}>
                            {r.title}
                          </td>
                          <td className="p-2 text-right">
                            <button
                              onClick={() => handleRollback(r.revision_number)}
                              disabled={rollingBackId !== null}
                              className="bg-amber-600 hover:bg-amber-500 text-black px-2 py-0.5 font-bold uppercase tracking-wider disabled:opacity-30 transition-colors text-[8px]"
                            >
                              {rollingBackId === r.revision_number ? "ROLLING..." : "REVERT"}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
