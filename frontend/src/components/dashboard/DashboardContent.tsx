"use client";

import React from "react";
import { useDashboard } from "@/components/providers/DashboardProvider";
import { Clock, Compass, User, History, Sparkles } from "lucide-react";
import { dashboardWidgets } from "./registry";
import { EmptyState, EmptyIllustration } from "@/components/common/EmptyState";

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
        <EmptyState size="lg">
          <EmptyIllustration
            icon={History}
            title="No reading history"
            description="Articles you read will appear here."
          />
        </EmptyState>
      )}

      {activeTab === "recommendations" && (
        <EmptyState size="lg">
          <EmptyIllustration
            icon={Sparkles}
            title="No recommendations"
            description="We are computing your personalized feed."
          />
        </EmptyState>
      )}

      {activeTab === "account" && (
        <div className="max-w-xl mx-auto border border-border/40 bg-card p-8 rounded-xl space-y-6 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center gap-3 border-b border-border/50 pb-3">
              <User className="w-5 h-5 text-primary" />
              <h2 className="text-xl font-bold text-foreground">Account Center</h2>
            </div>
            <p className="text-sm text-muted-foreground">
              Management configurations for your identity and data. In Phase 8, this module will enable:
            </p>
            <ul className="space-y-2 text-xs text-muted-foreground pl-4 list-disc">
              <li>Developer API key issuance for raw articles extraction streams.</li>
              <li>Webhook registrations for real-time alerts on emergency/breaking events.</li>
              <li>Exporting reading metrics data in clean CSV and JSON envelopes.</li>
            </ul>
          </div>
          <div className="pt-2">
            <div className="inline-flex items-center gap-2 bg-primary/10 border border-primary/20 text-primary font-mono text-[10px] tracking-wider uppercase px-3 py-1 rounded">
              <span className="h-1.5 w-1.5 bg-primary rounded-full animate-pulse" />
              Coming in Phase 8
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
