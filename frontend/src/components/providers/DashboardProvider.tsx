"use client";

import React, { createContext, useContext, useState } from "react";

export type DashboardTab = "overview" | "history" | "bookmarks" | "recommendations" | "stats" | "preferences" | "account";

interface DashboardState {
  activeTab: DashboardTab;
  isSidebarOpen: boolean;
  widgetOrder: string[];
}

interface DashboardContextType extends DashboardState {
  setActiveTab: (tab: DashboardTab) => void;
  setSidebarOpen: (isOpen: boolean) => void;
  setWidgetOrder: (order: string[]) => void;
}

const defaultWidgets = [
  "continue_reading",
  "recent_searches",
  "favorite_topics",
  "reading_calendar",
  "recommendation_feed",
  "bookmarks",
  "statistics",
  "preferences"
];

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const [activeTab, setActiveTab] = useState<DashboardTab>("overview");
  const [isSidebarOpen, setSidebarOpen] = useState(false);
  const [widgetOrder, setWidgetOrder] = useState<string[]>(defaultWidgets);

  return (
    <DashboardContext.Provider value={{
      activeTab,
      isSidebarOpen,
      widgetOrder,
      setActiveTab,
      setSidebarOpen,
      setWidgetOrder
    }}>
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  const context = useContext(DashboardContext);
  if (context === undefined) {
    throw new Error("useDashboard must be used within a DashboardProvider");
  }
  return context;
}
