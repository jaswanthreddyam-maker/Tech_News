"use client";

import React from "react";
import { useDashboard, DashboardTab } from "@/components/providers/DashboardProvider";
import { LayoutDashboard, History, Bookmark, Sparkles, BarChart2, Settings, User } from "lucide-react";

export function DashboardLayoutUI({ children }: { children: React.ReactNode }) {
  const { activeTab, setActiveTab } = useDashboard();

  const navItems: { id: DashboardTab; label: string; icon: React.ReactNode }[] = [
    { id: "overview", label: "Overview", icon: <LayoutDashboard className="w-5 h-5" /> },
    { id: "history", label: "Reading History", icon: <History className="w-5 h-5" /> },
    { id: "bookmarks", label: "Bookmarks", icon: <Bookmark className="w-5 h-5" /> },
    { id: "recommendations", label: "Recommendations", icon: <Sparkles className="w-5 h-5" /> },
    { id: "stats", label: "Reading Statistics", icon: <BarChart2 className="w-5 h-5" /> },
    { id: "preferences", label: "Preferences", icon: <Settings className="w-5 h-5" /> },
    { id: "account", label: "Account", icon: <User className="w-5 h-5" /> },
  ];

  return (
    <div className="container mx-auto px-4 py-12 flex flex-col lg:flex-row gap-12 mt-16">
      {/* Sidebar Navigation */}
      <aside className="w-full lg:w-64 shrink-0">
        <div className="sticky top-24">
          <div className="mb-8">
            <h1 className="text-3xl font-serif font-bold text-foreground">Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-2 font-mono">Personalization & Settings</p>
          </div>
          
          <nav className="flex flex-col gap-1">
            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors w-full text-left ${
                    isActive 
                      ? "bg-primary text-primary-foreground" 
                      : "text-muted-foreground hover:bg-card hover:text-foreground"
                  }`}
                >
                  {item.icon}
                  {item.label}
                </button>
              );
            })}
          </nav>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 min-w-0 border border-border/50 bg-card/20 rounded-2xl p-6 lg:p-12">
        {children}
      </main>
    </div>
  );
}
