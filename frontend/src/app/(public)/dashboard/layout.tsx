import React from "react";
import { AuthGuard } from "@/components/common/AuthGuard";
import { DashboardProvider } from "@/components/providers/DashboardProvider";
import { DashboardLayoutUI } from "@/components/dashboard/DashboardLayoutUI";

export const metadata = {
  title: "Dashboard | Tech News",
  description: "Manage your reading history, bookmarks, and recommendations.",
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <DashboardProvider>
        <DashboardLayoutUI>
          {children}
        </DashboardLayoutUI>
      </DashboardProvider>
    </AuthGuard>
  );
}
