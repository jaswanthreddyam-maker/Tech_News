"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api/client";
import Link from "next/link";
import { format } from "date-fns";

export default function EditorialDashboard() {
  const [drafts, setDrafts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDrafts();
  }, []);

  const fetchDrafts = async () => {
    try {
      const data = await apiFetch("/editorial/drafts");
      setDrafts(data as any[]);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const createDraft = async () => {
    try {
      const title = prompt("Enter draft title:", "New Draft");
      if (!title) return;
      const data: any = await apiFetch("/editorial/drafts", {
        method: "POST",
        body: JSON.stringify({ title, content: "Start writing here...", workspace_id: 1, tags: [] }),
      });
      window.location.href = `/editorial/${data.id}`;
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) {
    return <div className="p-8 max-w-6xl mx-auto font-mono text-gray-500">Loading editorial dashboard...</div>;
  }

  const columns = ["DRAFT", "REVIEW", "CHANGES_REQUESTED", "APPROVED", "PUBLISHED", "ARCHIVED"];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 min-h-screen">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold font-mono">Editorial Kanban</h1>
        <button 
          onClick={createDraft}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
        >
          + New Draft
        </button>
      </div>

      <div className="flex gap-6 overflow-x-auto pb-4">
        {columns.map(status => {
          const colDrafts = drafts.filter(d => d.status === status);
          return (
            <div key={status} className="flex-none w-80 bg-gray-50 rounded-xl p-4 border border-gray-200 flex flex-col max-h-[80vh]">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-semibold text-gray-700 font-mono text-sm">{status.replace("_", " ")}</h3>
                <span className="bg-white border border-gray-200 text-xs px-2 py-1 rounded-full text-gray-500">{colDrafts.length}</span>
              </div>
              
              <div className="flex flex-col gap-3 overflow-y-auto pr-1">
                {colDrafts.length === 0 ? (
                  <div className="text-xs text-gray-400 font-mono text-center py-4 border border-dashed border-gray-300 rounded-lg">Empty</div>
                ) : (
                  colDrafts.map(draft => (
                    <Link href={`/editorial/${draft.id}`} key={draft.id}>
                      <div className="bg-white border border-gray-200 rounded-lg p-3 hover:border-primary-400 hover:shadow-md transition-all cursor-pointer">
                        <h4 className="font-medium text-gray-900 text-sm mb-1">{draft.title || "Untitled Draft"}</h4>
                        <p className="text-xs text-gray-500 line-clamp-2 mb-3">{draft.content}</p>
                        <div className="text-[10px] text-gray-400 flex justify-between items-center font-mono">
                          <span>{draft.category || "General"}</span>
                          <span suppressHydrationWarning>{format(new Date(draft.updated_at), "MMM d, HH:mm")}</span>
                        </div>
                      </div>
                    </Link>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
