"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api/client";
import Link from "next/link";
import { Skeleton } from "@/design-system/components/Skeleton";
import { useLoadingState } from "@/design-system/hooks/useLoadingState";
import { FolderOpen } from "lucide-react";
import { EmptyState, EmptyIllustration, EmptyAction } from "@/components/common/EmptyState";

import { notFound } from "next/navigation";

export default function WorkspacesPage() {
  if (true as boolean) {
    notFound();
  }
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    fetchWorkspaces();
  }, []);

  const fetchWorkspaces = async () => {
    try {
      const data = await apiFetch("/workspaces");
      setWorkspaces(data as any[]);
    } catch (err) {
      // eslint-disable-next-line no-console

    } finally {
      setLoading(false);
    }
  };

  const createWorkspace = async () => {
    setIsCreating(true);
    try {
      const name = prompt("Enter a name for your new Research Workspace:", "New Workspace");
      if (!name) return;
      const data: any = await apiFetch("/workspaces", {
        method: "POST",
        body: JSON.stringify({ name, description: "" }),
      });
      setWorkspaces([data, ...workspaces]);
      window.location.href = `/workspaces/${data.id}`;
    } catch (err) {
      // eslint-disable-next-line no-console

    } finally {
      setIsCreating(false);
    }
  };

  const loadingLevel = useLoadingState(loading);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8 min-h-screen">
        <div className="flex items-center justify-between mb-8">
          <Skeleton level={loadingLevel} className="h-9 w-64" />
          <Skeleton level={loadingLevel} className="h-9 w-36 rounded-lg" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-xl p-5 h-full flex flex-col">
              <Skeleton level={loadingLevel} className="h-6 w-3/4 mb-3" />
              <div className="space-y-2 flex-1">
                <Skeleton level={loadingLevel} className="h-4 w-full" />
                <Skeleton level={loadingLevel} className="h-4 w-4/5" />
              </div>
              <div className="mt-6 pt-3 border-t border-gray-100 flex justify-between">
                <Skeleton level={loadingLevel} className="h-3 w-24" />
                <Skeleton level={loadingLevel} className="h-3 w-16" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 min-h-screen">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold font-mono">Research Workspaces</h1>
        <button 
          onClick={createWorkspace}
          disabled={isCreating}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors disabled:opacity-50"
        >
          {isCreating ? "Creating..." : "+ New Workspace"}
        </button>
      </div>

      {workspaces.length === 0 ? (
        <EmptyState className="my-12">
          <EmptyIllustration
            icon={FolderOpen}
            title="No workspaces found"
            description="Create a workspace to start organizing your research."
          />
          <EmptyAction
            primaryAction={
              <button 
                onClick={createWorkspace}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-full text-sm font-medium hover:bg-primary/90 transition-colors"
              >
                Create Your First Workspace
              </button>
            }
          />
        </EmptyState>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {workspaces.map(w => (
            <Link href={`/workspaces/${w.id}`} key={w.id} className="block group">
              <div className="bg-white border border-gray-200 rounded-xl p-5 hover:border-primary-300 hover:shadow-md transition-all h-full flex flex-col">
                <h3 className="font-semibold text-lg text-gray-900 group-hover:text-primary-600 mb-2">{w.name}</h3>
                <p className="text-sm text-gray-500 flex-1">{w.description || "No description provided."}</p>
                <div className="mt-4 text-xs text-gray-400 font-mono flex items-center justify-between border-t border-gray-100 pt-3">
                  <span suppressHydrationWarning>Updated: {new Date(w.updated_at).toLocaleDateString('en-US', { timeZone: 'UTC' })}</span>
                  <span className="text-primary-600 flex items-center">
                    Open <svg className="w-3 h-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7"/></svg>
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
