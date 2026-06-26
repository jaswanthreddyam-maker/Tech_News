"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Calendar as CalendarIcon, CheckCircle2, Clock, AlertCircle, XCircle } from "lucide-react";

type Campaign = {
  id: number;
  briefing_id: number;
  campaign_name: string;
  status: string;
  created_at: string;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
};

export default function CampaignCalendar() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchCampaigns() {
      try {
        const res = await fetch("/api/v1/newsletter/campaigns");
        if (res.ok) {
          const data = await res.json();
          setCampaigns(data);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchCampaigns();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "COMPLETED":
        return <Badge className="bg-emerald-500/15 text-emerald-600 hover:bg-emerald-500/25 border-emerald-500/20"><CheckCircle2 className="w-3 h-3 mr-1"/> Completed</Badge>;
      case "SENDING":
        return <Badge variant="default" className="bg-blue-500/15 text-blue-600 hover:bg-blue-500/25 border-blue-500/20 animate-pulse"><Clock className="w-3 h-3 mr-1"/> Sending</Badge>;
      case "SCHEDULED":
        return <Badge variant="outline" className="bg-amber-500/15 text-amber-600 hover:bg-amber-500/25 border-amber-500/20"><CalendarIcon className="w-3 h-3 mr-1"/> Scheduled</Badge>;
      case "FAILED":
        return <Badge variant="destructive"><AlertCircle className="w-3 h-3 mr-1"/> Failed</Badge>;
      case "CANCELLED":
        return <Badge variant="secondary"><XCircle className="w-3 h-3 mr-1"/> Cancelled</Badge>;
      case "DRAFT":
      default:
        return <Badge variant="outline">Draft</Badge>;
    }
  };

  if (loading) return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading Calendar...</div>;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Campaign Calendar</CardTitle>
        <CardDescription>All scheduled and historical newsletter dispatches.</CardDescription>
      </CardHeader>
      <CardContent>
        {campaigns.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            No campaigns found.
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Campaign ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Scheduled For</TableHead>
                <TableHead>Completed At</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {campaigns.map((camp) => (
                <TableRow key={camp.id}>
                  <TableCell className="font-medium">#{camp.id}</TableCell>
                  <TableCell>{camp.campaign_name}</TableCell>
                  <TableCell>{getStatusBadge(camp.status)}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {camp.scheduled_at ? new Date(camp.scheduled_at).toLocaleString() : new Date(camp.created_at).toLocaleString()}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {camp.completed_at ? new Date(camp.completed_at).toLocaleString() : "-"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
