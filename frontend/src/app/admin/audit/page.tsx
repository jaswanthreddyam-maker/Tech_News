/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../../../services/api";
import { ScrollText, RefreshCw, AlertCircle, ChevronLeft, ChevronRight } from "lucide-react";
import { EmptyState, EmptyIllustration } from "@/components/common/EmptyState";

interface AuditLog {
  id: number;
  user_email: string;
  action: string;
  resource: string;
  metadata: any;
  ip_address: string | null;
  device: string | null;
  created_at: string;
}

interface PaginatedAuditLogs {
  data: AuditLog[];
  pagination: {
    next_cursor: string | null;
    has_more: boolean;
    limit: number;
  };
}

export default function AdminAuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [cursorStack, setCursorStack] = useState<(string | null)[]>([null]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  // Filters State
  const [actionFilter, setActionFilter] = useState("");
  const [userFilterInput, setUserFilterInput] = useState("");
  const [userFilter, setUserFilter] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  // Debounce Operator filter text input
  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      setUserFilter(userFilterInput);
    }, 400);
    return () => clearTimeout(delayDebounce);
  }, [userFilterInput]);

  const fetchLogs = async (cursor: string | null = null, isSilent = false) => {
    if (!isSilent) setLoading(true);
    else setRefreshing(true);
    try {
      const params: Record<string, string> = { limit: "30" };
      if (cursor) params.cursor = cursor;
      if (actionFilter) params.action_filter = actionFilter;
      if (userFilter.trim()) params.user_filter = userFilter.trim();
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;

      const res = await apiFetch<PaginatedAuditLogs>("/admin/audit-logs", { params });
      setLogs(res && Array.isArray(res.data) ? res.data : []);
      setHasMore(res && res.pagination ? !!res.pagination.has_more : false);
      
      // Update cursors for pagination
      if (res && res.pagination && res.pagination.next_cursor) {
        if (!cursorStack.includes(res.pagination.next_cursor)) {
          setCursorStack((prev) => [...prev, res.pagination.next_cursor]);
        }
      }
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to retrieve historical audit logs.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchLogs(cursorStack[currentIndex]);
  }, [currentIndex]);

  // Reset pagination when filters change
  useEffect(() => {
    setCursorStack([null]);
    if (currentIndex === 0) {
      fetchLogs(null);
    } else {
      setCurrentIndex(0);
    }
  }, [actionFilter, userFilter, startDate, endDate]);

  const handleNext = () => {
    if (hasMore) {
      setCurrentIndex((prev) => prev + 1);
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex((prev) => prev - 1);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 font-mono text-[11px]">
        <div className="h-4 bg-neutral-900 w-48 animate-pulse" />
        <div className="border border-[#1a1a1a] bg-black p-4 space-y-4">
          <div className="h-8 bg-neutral-950 animate-pulse w-full border-b border-[#111]" />
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
          <ScrollText className="w-3.5 h-3.5 text-[#888]" />
          <h1 className="font-mono text-[11px] tracking-widest uppercase text-white font-bold">
            PLATFORM OPERATIONS AUDIT LOGS
          </h1>
        </div>
        <button
          onClick={() => fetchLogs(cursorStack[currentIndex], true)}
          disabled={refreshing}
          className="flex items-center gap-1.5 font-mono text-[9px] tracking-widest uppercase text-[#888] hover:text-white transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${refreshing ? "animate-spin" : ""}`} />
          REFRESH
        </button>
      </div>

      {/* Filters Bar */}
      <div className="border border-[#1a1a1a] bg-[#0c0c0c] p-3 grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="action-filter" className="font-mono text-[9px] tracking-widest uppercase text-[#555] select-none">
            ACTION EVENT
          </label>
          <select
            id="action-filter"
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="w-full bg-black border border-[#1a1a1a] px-2.5 py-1.5 font-mono text-[11px] text-white focus:outline-none focus:border-white transition-colors"
          >
            <option value="">ALL EVENTS</option>
            <option value="UPDATE_SOURCE">UPDATE_SOURCE</option>
            <option value="DELETE_SOURCE">DELETE_SOURCE</option>
            <option value="RESTORE_SOURCE">RESTORE_SOURCE</option>
            <option value="TOGGLE_SOURCE">TOGGLE_SOURCE</option>
            <option value="TRIGGER_CRAWL">TRIGGER_CRAWL</option>
            <option value="MODERATE_ARTICLE">MODERATE_ARTICLE</option>
            <option value="UPDATE_USER_ROLE">UPDATE_USER_ROLE</option>
            <option value="UPDATE_USER_STATUS">UPDATE_USER_STATUS</option>
            <option value="TOGGLE_FEATURE_FLAG">TOGGLE_FEATURE_FLAG</option>
            <option value="TOGGLE_EMERGENCY_CUTOFF">TOGGLE_EMERGENCY_CUTOFF</option>
            <option value="UPDATE_ARTICLE">UPDATE_ARTICLE</option>
            <option value="ROLLBACK_ARTICLE">ROLLBACK_ARTICLE</option>
          </select>
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="user-filter" className="font-mono text-[9px] tracking-widest uppercase text-[#555] select-none">
            OPERATOR EMAIL/ID
          </label>
          <input
            id="user-filter"
            type="text"
            value={userFilterInput}
            onChange={(e) => setUserFilterInput(e.target.value)}
            placeholder="EMAIL OR ID..."
            className="w-full bg-black border border-[#1a1a1a] px-2.5 py-1.5 font-mono text-[11px] text-white focus:outline-none focus:border-white placeholder-neutral-700 transition-colors"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="start-date" className="font-mono text-[9px] tracking-widest uppercase text-[#555] select-none">
            START DATE
          </label>
          <input
            id="start-date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full bg-black border border-[#1a1a1a] px-2.5 py-1.5 font-mono text-[11px] text-white focus:outline-none focus:border-white transition-colors"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="end-date" className="font-mono text-[9px] tracking-widest uppercase text-[#555] select-none">
            END DATE
          </label>
          <div className="flex gap-2">
            <input
              id="end-date"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="flex-1 bg-black border border-[#1a1a1a] px-2.5 py-1.5 font-mono text-[11px] text-white focus:outline-none focus:border-white transition-colors"
            />
            {(actionFilter || userFilterInput || startDate || endDate) && (
              <button
                onClick={() => {
                  setActionFilter("");
                  setUserFilterInput("");
                  setStartDate("");
                  setEndDate("");
                }}
                className="font-mono text-[9px] tracking-widest uppercase text-[#888] hover:text-white transition-colors border border-[#1a1a1a] px-2.5 py-1.5 bg-black text-center shrink-0"
              >
                RESET
              </button>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="border border-red-500/30 bg-red-500/5 px-3 py-2 flex items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
          <p className="font-mono text-[10px] text-red-400">{error}</p>
        </div>
      )}

      {/* Logs Table */}
      <div className="border border-[#1a1a1a] bg-black overflow-x-auto">
        <table className="w-full text-left font-mono text-[11px]">
          <thead>
            <tr className="border-b border-[#1a1a1a] bg-[#0c0c0c] text-[#555] select-none text-[9px]">
              <th className="p-3">TIMESTAMP</th>
              <th className="p-3">OPERATOR / EMAIL</th>
              <th className="p-3">ACTION EVENT</th>
              <th className="p-3">TARGET RESOURCE</th>
              <th className="p-3">IP ADDRESS</th>
              <th className="p-3 text-right">PAYLOAD METADATA</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#111]">
            {logs.map((l) => (
              <tr key={l.id} className="hover:bg-[#060606] transition-colors leading-relaxed">
                <td className="p-3 text-[#555]">{new Date(l.created_at).toLocaleString()}</td>
                <td className="p-3 text-white font-semibold">{l.user_email}</td>
                <td className="p-3">
                  <span className="inline-flex items-center px-1.5 py-0.5 text-[8px] font-bold tracking-wider uppercase border border-neutral-700 bg-neutral-900 text-[#ccc]">
                    {l.action}
                  </span>
                </td>
                <td className="p-3 text-[#888]">{l.resource}</td>
                <td className="p-3 text-[#555]">{l.ip_address || "System"}</td>
                <td className="p-3 text-right max-w-[200px] truncate text-[9px] text-[#888]" title={JSON.stringify(l.metadata)}>
                  {JSON.stringify(l.metadata)}
                </td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr>
                <td colSpan={6} className="p-8">
                  <EmptyState size="sm">
                    <EmptyIllustration
                      icon={ScrollText}
                      title="No audit logs found"
                      description="No administrative audit records matched the criteria."
                    />
                  </EmptyState>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      <div className="flex justify-between items-center font-mono text-[9px] tracking-widest uppercase text-[#555] pt-2">
        <button
          onClick={handlePrev}
          disabled={currentIndex === 0}
          className="flex items-center gap-1 hover:text-white disabled:opacity-30 disabled:hover:text-[#555] transition-colors"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
          PREVIOUS
        </button>
        <span>PAGE {currentIndex + 1}</span>
        <button
          onClick={handleNext}
          disabled={!hasMore}
          className="flex items-center gap-1 hover:text-white disabled:opacity-30 disabled:hover:text-[#555] transition-colors"
        >
          NEXT
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
