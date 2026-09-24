import React from "react";
import { DashboardContent } from "@/components/dashboard/DashboardContent";

export const metadata = {
  title: "Dashboard | Tech News",
  description: "Manage your reading history, bookmarks, and recommendations.",
};

export default function DashboardPage() {
  return <DashboardContent />;
}
