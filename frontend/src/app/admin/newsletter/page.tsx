"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import DraftQueue from "./components/DraftQueue";
import ReviewApprovalQueue from "./components/ReviewApprovalQueue";
import CampaignCalendar from "./components/CampaignCalendar";
import CampaignAnalytics from "./components/CampaignAnalytics";
import { BookOpen, Calendar, LineChart, ListChecks } from "lucide-react";

export default function EditorialNewsletterDashboard() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Editorial Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Review, approve, and analyze daily newsletter briefings.
          </p>
        </div>
      </div>

      <Tabs defaultValue="drafts" className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="drafts" className="flex items-center gap-2">
            <BookOpen className="h-4 w-4" />
            Draft Queue
          </TabsTrigger>
          <TabsTrigger value="review" className="flex items-center gap-2">
            <ListChecks className="h-4 w-4" />
            Review & Approve
          </TabsTrigger>
          <TabsTrigger value="calendar" className="flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            Campaign Calendar
          </TabsTrigger>
          <TabsTrigger value="analytics" className="flex items-center gap-2">
            <LineChart className="h-4 w-4" />
            Analytics
          </TabsTrigger>
        </TabsList>

        <TabsContent value="drafts" className="mt-0">
          <DraftQueue />
        </TabsContent>
        <TabsContent value="review" className="mt-0">
          <ReviewApprovalQueue />
        </TabsContent>
        <TabsContent value="calendar" className="mt-0">
          <CampaignCalendar />
        </TabsContent>
        <TabsContent value="analytics" className="mt-0">
          <CampaignAnalytics />
        </TabsContent>
      </Tabs>
    </div>
  );
}
