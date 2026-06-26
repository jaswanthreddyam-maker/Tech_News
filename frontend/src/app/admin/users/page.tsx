"use client";

import { useEffect, useState, useCallback } from "react";
import { apiFetch } from "../../../services/api";
import { useAppStore } from "../../../store/useStore";
import { canPromoteUsers, canModifyUserStatus } from "../../../lib/auth/permissions";
import { Users, AlertCircle, RefreshCw, ShieldAlert, ShieldCheck } from "lucide-react";
import { EmptyState, EmptyIllustration } from "@/components/common/EmptyState";

interface UserRecord {
  id: number;
  name: string;
  email: string;
  role: string | null;
  status: string;
  created_at: string;
}

export default function AdminUsersPage() {
  const { user: currentUser } = useAppStore();
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [actingUserId, setActingUserId] = useState<number | null>(null);
  
  // Search query states
  const [searchQuery, setSearchQuery] = useState("");
  const [isFirstLoad, setIsFirstLoad] = useState(true);
  const fetchUsers = useCallback(async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    else setRefreshing(true);
    try {
      const params: Record<string, string> = {};
      if (searchQuery.trim()) {
        params.q = searchQuery.trim();
      }
      const data = await apiFetch<UserRecord[]>("/admin/users", { params });
      setUsers(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load platform user index.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [searchQuery]);

  useEffect(() => {
    if (isFirstLoad) {
      fetchUsers(false);
      setIsFirstLoad(false);
      return;
    }
    const delayDebounce = setTimeout(() => {
      fetchUsers(true);
    }, 300);
    return () => clearTimeout(delayDebounce);
  }, [fetchUsers, isFirstLoad]);
  const handleRoleChange = async (userId: number, role: string) => {
    setActingUserId(userId);
    setMessage(null);
    try {
      const res: any = await apiFetch(`/admin/users/${userId}/role`, {
        method: "PUT",
        body: JSON.stringify({ role }),
      });
      setUsers((prev) =>
        (Array.isArray(prev) ? prev : []).map((u) => (u.id === userId ? { ...u, role } : u))
      );
      setMessage(res.message);
    } catch (err: any) {
      setError(err.message || "Role promotion failed.");
    } finally {
      setActingUserId(null);
    }
  };

  const handleStatusChange = async (userId: number, status: string) => {
    setActingUserId(userId);
    setMessage(null);
    try {
      const res: any = await apiFetch(`/admin/users/${userId}/status`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      });
      setUsers((prev) =>
        (Array.isArray(prev) ? prev : []).map((u) => (u.id === userId ? { ...u, status } : u))
      );
      setMessage(res.message);
    } catch (err: any) {
      setError(err.message || "Status change failed.");
    } finally {
      setActingUserId(null);
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
          <Users className="w-3.5 h-3.5 text-[#888]" />
          <h1 className="font-mono text-[11px] tracking-widest uppercase text-white font-bold">
            PLATFORM USER ACCOUNTS
          </h1>
        </div>
        <button
          onClick={() => fetchUsers(true)}
          disabled={refreshing}
          className="flex items-center gap-1.5 font-mono text-[9px] tracking-widest uppercase text-[#888] hover:text-white transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${refreshing ? "animate-spin" : ""}`} />
          REFRESH
        </button>
      </div>

      {/* Search Filter */}
      <div className="border border-[#1a1a1a] bg-[#0c0c0c] p-3 flex items-center gap-3">
        <span className="font-mono text-[9px] tracking-widest uppercase text-[#555] select-none shrink-0">
          SEARCH USERS:
        </span>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="ENTER OPERATOR NAME OR EMAIL ADDRESS..."
          className="flex-1 bg-black border border-[#1a1a1a] px-2.5 py-1.5 font-mono text-[11px] text-white focus:outline-none focus:border-white placeholder-neutral-700 transition-colors"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery("")}
            className="font-mono text-[9px] tracking-widest uppercase text-[#888] hover:text-white transition-colors border border-[#1a1a1a] px-2.5 py-1.5 bg-black"
          >
            CLEAR
          </button>
        )}
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

      {/* Users table */}
      <div className="border border-[#1a1a1a] bg-black overflow-x-auto">
        <table className="w-full text-left font-mono text-[11px]">
          <caption className="sr-only">Platform User Accounts</caption>
          <thead>
            <tr className="border-b border-[#1a1a1a] bg-[#0c0c0c] text-[#555] select-none text-[9px]">
              <th scope="col" className="p-3">ID</th>
              <th scope="col" className="p-3">USER NAME</th>
              <th scope="col" className="p-3">EMAIL ADDRESS</th>
              <th scope="col" className="p-3">ROLE AUTHORITY</th>
              <th scope="col" className="p-3">ACCOUNT STATE</th>
              <th scope="col" className="p-3 text-right">TOGGLE STATE</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#111]">
            {users.map((u) => (
              <tr key={u.id} className="hover:bg-[#060606] transition-colors">
                <td className="p-3 text-[#555]">{u.id}</td>
                <td className="p-3 text-white font-semibold">{u.name}</td>
                <td className="p-3 text-[#888]">{u.email}</td>
                <td className="p-3">
                  <select
                    value={u.role || ""}
                    disabled={actingUserId !== null || !canPromoteUsers(currentUser)}
                    onChange={(e) => handleRoleChange(u.id, e.target.value)}
                    aria-label={`Change role for ${u.name}`}
                    className="bg-[#080808] border border-[#1a1a1a] text-[#ccc] py-0.5 px-1.5 focus:outline-none focus:border-white text-[10px] disabled:opacity-50"
                  >
                    <option value="reader">reader</option>
                    <option value="editor">editor</option>
                    <option value="admin">admin</option>
                    <option value="super_admin">super_admin</option>
                  </select>
                </td>
                <td className="p-3">
                  <span
                    className={`inline-flex items-center px-1.5 py-0.5 text-[8px] font-bold tracking-wider uppercase border ${
                      u.status === "active"
                        ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-400"
                        : "border-red-500/20 bg-red-500/5 text-red-400"
                    }`}
                  >
                    {u.status}
                  </span>
                </td>
                <td className="p-3 text-right">
                  <button
                    onClick={() =>
                      handleStatusChange(u.id, u.status === "active" ? "disabled" : "active")
                    }
                    disabled={actingUserId !== null || !canModifyUserStatus(currentUser, u)}
                    className="font-mono text-[9px] tracking-wider uppercase bg-foreground text-background px-2.5 py-1 hover:bg-neutral-300 disabled:opacity-30 transition-colors"
                  >
                    {u.status === "active" ? "SUSPEND" : "ACTIVATE"}
                  </button>
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={6} className="p-8">
                  <EmptyState size="sm">
                    <EmptyIllustration
                      icon={Users}
                      title="No users found"
                      description="No users match the active search filters."
                    />
                  </EmptyState>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
