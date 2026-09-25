"use client";

import React from "react";
import Link from "next/link";
import { useDashboard } from "@/components/providers/DashboardProvider";
import { Clock, Compass, User, History, Sparkles, Settings } from "lucide-react";
import { dashboardWidgets } from "./registry";
import { ReadingHistoryList } from "./ReadingHistoryList";
import { RecommendationsList } from "./RecommendationsList";

export function DashboardContent() {
  const { activeTab } = useDashboard();

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      {activeTab === "overview" && (
        <div className="space-y-12">
          <section>
            <h2 className="text-2xl font-serif font-bold mb-6">Welcome Back</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {dashboardWidgets.map(widget => {
                const WidgetComponent = widget.component;
                return widget.id !== "bookmarks" ? <WidgetComponent key={widget.id} compact /> : null;
              })}
            </div>
          </section>
          
          <section>
            <h3 className="text-xl font-bold mb-6">Recent Bookmarks</h3>
            {React.createElement(dashboardWidgets.find(w => w.id === "bookmarks")?.component as any, { limit: 3 })}
          </section>
        </div>
      )}

      {activeTab === "bookmarks" && (
        <div>
          <h2 className="text-2xl font-serif font-bold mb-6">Your Bookmarks</h2>
          {React.createElement(dashboardWidgets.find(w => w.id === "bookmarks")?.component as any)}
        </div>
      )}

      {activeTab === "stats" && (
        <div>
          <h2 className="text-2xl font-serif font-bold mb-6">Reading Statistics</h2>
          {React.createElement(dashboardWidgets.find(w => w.id === "stats")?.component as any)}
        </div>
      )}

      {activeTab === "preferences" && (
        <div>
          <h2 className="text-2xl font-serif font-bold mb-6">Recommendation Preferences</h2>
          {React.createElement(dashboardWidgets.find(w => w.id === "preferences")?.component as any)}
        </div>
      )}

      {activeTab === "history" && (
        <div>
          <h2 className="text-2xl font-serif font-bold mb-6">Your Reading History</h2>
          <ReadingHistoryList />
        </div>
      )}

      {activeTab === "recommendations" && (
        <div>
          <h2 className="text-2xl font-serif font-bold mb-6">Personalized Recommendations</h2>
          <RecommendationsList />
        </div>
      )}

      {activeTab === "account" && (
        <div className="max-w-xl mx-auto border border-border/40 bg-card p-8 rounded-xl space-y-6 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center gap-3 border-b border-border/50 pb-3">
              <User className="w-5 h-5 text-primary" />
              <h2 className="text-xl font-bold text-foreground">Account & Settings</h2>
            </div>
            <p className="text-sm text-muted-foreground">
              Manage your personal credentials, active sessions, daily briefing subscription, and notifications in the canonical settings center.
            </p>
          </div>
          <div className="pt-2">
            <Link
              href="/dashboard/settings"
              className="inline-flex items-center gap-2 bg-primary text-primary-foreground font-mono text-xs font-semibold px-4 py-2.5 rounded-xl hover:bg-primary/90 transition-all cursor-pointer shadow-sm"
            >
              <span>Open Settings & Preferences</span>
              <Settings className="w-4 h-4" />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
