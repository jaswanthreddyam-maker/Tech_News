import React from "react";
import { DashboardProvider } from "@/components/providers/DashboardProvider";
import { DashboardContent } from "@/components/dashboard/DashboardContent";

export const metadata = {
  title: "Dashboard | Tech News",
  description: "Manage your reading history, bookmarks, and recommendations.",
};

export default function DashboardPage() {
  return (
    <DashboardProvider>
      <DashboardContent />
    </DashboardProvider>
  );
}
