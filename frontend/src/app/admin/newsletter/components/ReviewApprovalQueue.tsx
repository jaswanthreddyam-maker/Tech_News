"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, XCircle, Clock } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

type Version = {
  id: number;
  version_number: number;
  title: string;
  created_by: string | null;
  source: string;
  created_at: string;
  content_html: string;
  content_text: string;
};

type Briefing = {
  id: number;
  status: string;
  current_version_id: number | null;
  created_at: string;
  versions: Version[];
};

export default function ReviewApprovalQueue() {
  const [drafts, setDrafts] = useState<Briefing[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const fetchDrafts = async () => {
    try {
      const res = await fetch("/api/v1/newsletter/briefings");
      if (res.ok) {
        const data: Briefing[] = await res.json();
        setDrafts(data.filter(b => b.status === "DRAFT"));
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDrafts();
  }, []);

  const handleApprove = async (id: number) => {
    try {
      const res = await fetch(`/api/v1/newsletter/briefings/${id}/approve`, { method: "POST" });
      if (res.ok) {
        toast({ title: "Approved", description: `Briefing #${id} approved.` });
        fetchDrafts();
      } else {
        const err = await res.json();
        toast({ variant: "destructive", title: "Error", description: err.detail });
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleReject = async (id: number) => {
    try {
      const res = await fetch(`/api/v1/newsletter/briefings/${id}/reject`, { method: "POST" });
      if (res.ok) {
        toast({ title: "Rejected", description: `Briefing #${id} rejected.` });
        fetchDrafts();
      }
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading Review Queue...</div>;

  return (
    <div className="space-y-6">
      {drafts.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No drafts pending review.
          </CardContent>
        </Card>
      ) : (
        drafts.map((draft) => {
          const latestVersion = draft.versions[0];
          const v1 = draft.versions[draft.versions.length - 1]; // Oldest version
          
          return (
            <Card key={draft.id} className="overflow-hidden">
              <CardHeader className="bg-muted/40 border-b">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-xl">Briefing #{draft.id}</CardTitle>
                    <CardDescription className="flex items-center gap-2 mt-1">
                      <Clock className="h-3 w-3" />
                      Created {new Date(draft.created_at).toLocaleString()}
                    </CardDescription>
                  </div>
                  <Badge variant={draft.versions.length > 1 ? "secondary" : "outline"}>
                    {draft.versions.length > 1 ? "Edited" : "AI Generated"}
                  </Badge>
                </div>
              </CardHeader>
              
              <CardContent className="p-0">
                <div className="grid grid-cols-2 divide-x">
                  <div className="p-6 space-y-4">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">Version 1 (AI_GENERATED)</Badge>
                    </div>
                    <div className="prose prose-sm dark:prose-invert max-w-none opacity-70">
                      <h3 className="text-lg font-bold">{v1?.title}</h3>
                      <div dangerouslySetInnerHTML={{ __html: v1?.content_html || "" }} />
                    </div>
                  </div>
                  <div className="p-6 space-y-4 bg-muted/10">
                    <div className="flex items-center gap-2">
                      <Badge>Current Draft (v{latestVersion?.version_number})</Badge>
                      <span className="text-xs text-muted-foreground">by {latestVersion?.created_by || "System"}</span>
                    </div>
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <h3 className="text-lg font-bold">{latestVersion?.title}</h3>
                      <div dangerouslySetInnerHTML={{ __html: latestVersion?.content_html || "" }} />
                    </div>
                  </div>
                </div>
              </CardContent>
              
              <CardFooter className="bg-muted/40 border-t p-4 flex justify-end gap-4">
                <Button variant="outline" className="text-destructive hover:bg-destructive/10" onClick={() => handleReject(draft.id)}>
                  <XCircle className="h-4 w-4 mr-2" />
                  Reject
                </Button>
                <Button className="bg-primary hover:bg-primary/90" onClick={() => handleApprove(draft.id)}>
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                  Approve & Schedule
                </Button>
              </CardFooter>
            </Card>
          );
        })
      )}
    </div>
  );
}
