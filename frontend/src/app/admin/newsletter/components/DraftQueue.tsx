"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Clock, FileEdit, User } from "lucide-react";

type Version = {
  id: number;
  version_number: number;
  title: string;
  created_by: string | null;
  source: string;
  created_at: string;
};

type Briefing = {
  id: number;
  status: string;
  current_version_id: number | null;
  created_at: string;
  versions: Version[];
};

export default function DraftQueue() {
  const [drafts, setDrafts] = useState<Briefing[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchDrafts() {
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
    }
    fetchDrafts();
  }, []);

  if (loading) return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading Draft Queue...</div>;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Draft Queue</CardTitle>
          <CardDescription>Briefings that are currently being written or edited.</CardDescription>
        </CardHeader>
        <CardContent>
          {drafts.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              No drafts currently in the queue.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Briefing ID</TableHead>
                  <TableHead>Current Version</TableHead>
                  <TableHead>Last Edited By</TableHead>
                  <TableHead>Last Edited At</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {drafts.map((draft) => {
                  // Versions are ordered descending in API
                  const latestVersion = draft.versions[0];
                  return (
                    <TableRow key={draft.id}>
                      <TableCell className="font-medium">#{draft.id}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">v{latestVersion?.version_number || 1}</Badge>
                          <span className="text-muted-foreground text-sm">
                            ({draft.versions.length} total)
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2 text-sm">
                          <User className="h-3 w-3 text-muted-foreground" />
                          {latestVersion?.created_by || "System"}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          {new Date(latestVersion?.created_at || draft.created_at).toLocaleString()}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm" className="gap-2">
                          <FileEdit className="h-4 w-4" />
                          Edit
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
