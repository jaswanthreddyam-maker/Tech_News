"use client";

import React, { Suspense, useEffect } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useDashboard, DashboardTab } from "@/components/providers/DashboardProvider";
import {
  LayoutDashboard,
  Bookmark,
  History,
  BarChart2,
  Sparkles,
  SlidersHorizontal,
  Settings,
} from "lucide-react";

interface NavItem {
  id: DashboardTab | "settings";
  label: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { id: "overview", label: "Overview", icon: <LayoutDashboard className="w-5 h-5" /> },
  { id: "bookmarks", label: "Bookmarks", icon: <Bookmark className="w-5 h-5" /> },
  { id: "history", label: "Reading History", icon: <History className="w-5 h-5" /> },
  { id: "stats", label: "Reading Statistics", icon: <BarChart2 className="w-5 h-5" /> },
  { id: "recommendations", label: "Recommendations", icon: <Sparkles className="w-5 h-5" /> },
  { id: "preferences", label: "Feed Preferences", icon: <SlidersHorizontal className="w-5 h-5" /> },
  { id: "settings", label: "Settings & Preferences", icon: <Settings className="w-5 h-5" /> },
];

function DashboardSidebarNav() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { activeTab, setActiveTab } = useDashboard();

  const isSettingsPage = pathname === "/dashboard/settings";

  // Sync tab with URL query parameter when on /dashboard
  useEffect(() => {
    if (pathname === "/dashboard") {
      const tabParam = searchParams.get("tab") as DashboardTab | null;
      const validTabs: DashboardTab[] = [
        "overview",
        "bookmarks",
        "history",
        "stats",
        "recommendations",
        "preferences",
      ];
      if (tabParam && validTabs.includes(tabParam)) {
        setActiveTab(tabParam);
      } else if (!tabParam) {
        setActiveTab("overview");
      }
    }
  }, [pathname, searchParams, setActiveTab]);

  const handleNavClick = (id: DashboardTab | "settings") => {
    if (id === "settings") {
      if (!isSettingsPage) {
        router.push("/dashboard/settings");
      }
      return;
    }

    setActiveTab(id);
    const targetUrl = id === "overview" ? "/dashboard" : `/dashboard?tab=${id}`;
    if (isSettingsPage) {
      router.push(targetUrl);
    } else {
      router.push(targetUrl, { scroll: false });
    }
  };

  return (
    <nav className="flex flex-col gap-1">
      {navItems.map((item) => {
        const isActive =
          item.id === "settings"
            ? isSettingsPage
            : !isSettingsPage && activeTab === item.id;

        return (
          <button
            key={item.id}
            type="button"
            onClick={() => handleNavClick(item.id)}
            className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors w-full text-left cursor-pointer ${
              isActive
                ? "bg-primary text-primary-foreground font-semibold shadow-sm"
                : "text-muted-foreground hover:bg-card hover:text-foreground"
            }`}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

export function DashboardLayoutUI({ children }: { children: React.ReactNode }) {
  return (
    <div className="container mx-auto px-4 py-12 flex flex-col lg:flex-row gap-12 mt-16">
      {/* Sidebar Navigation */}
      <aside className="w-full lg:w-64 shrink-0">
        <div className="sticky top-24">
          <div className="mb-8">
            <h1 className="text-3xl font-serif font-bold text-foreground">Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-2 font-mono">Personalization & Settings</p>
          </div>

          <Suspense
            fallback={
              <div className="flex flex-col gap-1 animate-pulse">
                {[1, 2, 3, 4, 5, 6, 7].map((i) => (
                  <div key={i} className="h-11 rounded-lg bg-card/40" />
                ))}
              </div>
            }
          >
            <DashboardSidebarNav />
          </Suspense>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 min-w-0 border border-border/50 bg-card/20 rounded-2xl p-6 lg:p-12">
        {children}
      </main>
    </div>
  );
}
