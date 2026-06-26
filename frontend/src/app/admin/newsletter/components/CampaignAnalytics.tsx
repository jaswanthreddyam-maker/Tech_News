"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Mail, MousePointerClick, AlertTriangle, UserMinus, Send, BarChart3 } from "lucide-react";

type Campaign = {
  id: number;
  campaign_name: string;
  status: string;
};

type Analytics = {
  campaign_id: number;
  total_recipients: number;
  sent_count: number;
  delivered_count: number;
  opened_count: number;
  clicked_count: number;
  bounced_count: number;
  failed_count: number;
  open_rate: string;
  click_rate: string;
  bounce_rate: string;
  unsubscribe_rate: string;
  delivery_rate: string;
};

export default function CampaignAnalytics() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState<string>("");
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchCampaigns() {
      try {
        const res = await fetch("/api/v1/newsletter/campaigns");
        if (res.ok) {
          const data = await res.json();
          // Only show analytics for sent/completed
          const sent = data.filter((c: Campaign) => ["SENDING", "COMPLETED"].includes(c.status));
          setCampaigns(sent);
          if (sent.length > 0) {
            setSelectedCampaign(sent[0].id.toString());
          }
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchCampaigns();
  }, []);

  useEffect(() => {
    if (!selectedCampaign) return;
    async function fetchAnalytics() {
      try {
        const res = await fetch(`/api/v1/newsletter/campaigns/${selectedCampaign}/analytics`);
        if (res.ok) {
          const data = await res.json();
          setAnalytics(data);
        } else {
          setAnalytics(null);
        }
      } catch (err) {
        console.error(err);
        setAnalytics(null);
      }
    }
    fetchAnalytics();
  }, [selectedCampaign]);

  if (loading) return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading Analytics...</div>;

  if (campaigns.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          No sent campaigns available for analytics yet.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold tracking-tight flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-primary" />
          Campaign Performance
        </h2>
        <div className="w-72">
          <Select value={selectedCampaign} onValueChange={setSelectedCampaign}>
            <SelectTrigger>
              <SelectValue placeholder="Select a campaign" />
            </SelectTrigger>
            <SelectContent>
              {campaigns.map((c) => (
                <SelectItem key={c.id} value={c.id.toString()}>
                  {c.campaign_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {analytics ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Delivery Rate</CardTitle>
              <Send className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{analytics.delivery_rate}%</div>
              <p className="text-xs text-muted-foreground mt-1">
                {analytics.sent_count} / {analytics.total_recipients} recipients
              </p>
              <div className="mt-4 h-2 w-full bg-secondary rounded-full overflow-hidden">
                <div 
                  className="h-full bg-emerald-500" 
                  style={{ width: `${Math.min(100, Number(analytics.delivery_rate))}%` }} 
                />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Open Rate</CardTitle>
              <Mail className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{analytics.open_rate}%</div>
              <p className="text-xs text-muted-foreground mt-1">
                {analytics.opened_count} opened unique
              </p>
              <div className="mt-4 h-2 w-full bg-secondary rounded-full overflow-hidden">
                <div 
                  className="h-full bg-blue-500" 
                  style={{ width: `${Math.min(100, Number(analytics.open_rate))}%` }} 
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Click Rate</CardTitle>
              <MousePointerClick className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{analytics.click_rate}%</div>
              <p className="text-xs text-muted-foreground mt-1">
                {analytics.clicked_count} clicks
              </p>
              <div className="mt-4 h-2 w-full bg-secondary rounded-full overflow-hidden">
                <div 
                  className="h-full bg-violet-500" 
                  style={{ width: `${Math.min(100, Number(analytics.click_rate))}%` }} 
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Health Metrics</CardTitle>
              <AlertTriangle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground flex items-center gap-1">
                    <UserMinus className="h-3 w-3" /> Unsubscribes
                  </span>
                  <span className="text-sm font-medium">{analytics.unsubscribe_rate}%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" /> Bounces
                  </span>
                  <span className="text-sm font-medium">{analytics.bounce_rate}%</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No analytics data found for this campaign.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
