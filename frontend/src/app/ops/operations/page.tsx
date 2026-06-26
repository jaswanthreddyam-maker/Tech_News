"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Activity, ArrowRight, CheckCircle2, Clock, XCircle } from "lucide-react";

export default function OperationsPage() {
  const [operations, setOperations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Stub for GET /admin/operations
    setTimeout(() => {
      setOperations([
        {
          operation_id: "op_9f8e7d2a",
          status: "COMPLETED",
          artifact_id: "art_112233",
          message: "Research complete.",
          created_at: "2026-06-14T10:00:00Z"
        },
        {
          operation_id: "op_4b5c6d7e",
          status: "RUNNING",
          artifact_id: null,
          message: "Executing planner...",
          created_at: "2026-06-14T10:05:00Z"
        }
      ]);
      setLoading(false);
    }, 500);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "COMPLETED": return <CheckCircle2 className="w-5 h-5 text-emerald-500" />;
      case "RUNNING": return <Activity className="w-5 h-5 text-blue-500 animate-pulse" />;
      case "FAILED": return <XCircle className="w-5 h-5 text-rose-500" />;
      default: return <Clock className="w-5 h-5 text-slate-500" />;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Operations Trace</h1>
        <p className="text-slate-400">External requests submitted to the Enterprise Gateway.</p>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-800/50 text-slate-300 border-b border-slate-800">
            <tr>
              <th className="px-6 py-4 font-medium">Operation ID</th>
              <th className="px-6 py-4 font-medium">Status</th>
              <th className="px-6 py-4 font-medium">Message</th>
              <th className="px-6 py-4 font-medium">Created At</th>
              <th className="px-6 py-4 font-medium text-right">Trace Goal</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {loading ? (
              <tr><td colSpan={5} className="px-6 py-4 text-center text-slate-500">Loading...</td></tr>
            ) : operations.map((op) => (
              <tr key={op.operation_id} className="hover:bg-slate-800/50 transition-colors">
                <td className="px-6 py-4 font-mono text-slate-300">{op.operation_id}</td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(op.status)}
                    <span className="font-medium text-slate-200">{op.status}</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-slate-400">{op.message}</td>
                <td className="px-6 py-4 text-slate-400">{new Date(op.created_at).toLocaleTimeString()}</td>
                <td className="px-6 py-4 text-right">
                  <Link 
                    href={`/ops/goals?op=${op.operation_id}`}
                    className="inline-flex items-center gap-1 text-blue-400 hover:text-blue-300"
                  >
                    Trace <ArrowRight className="w-4 h-4" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
