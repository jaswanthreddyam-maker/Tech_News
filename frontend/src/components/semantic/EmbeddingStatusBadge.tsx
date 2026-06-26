import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, Clock, XCircle, AlertCircle } from "lucide-react";

interface EmbeddingStatusBadgeProps {
  status: "pending" | "processing" | "completed" | "failed" | string;
}

export function EmbeddingStatusBadge({ status }: EmbeddingStatusBadgeProps) {
  const s = status.toLowerCase();

  if (s === "completed") {
    return (
      <Badge variant="outline" className="bg-success/10 text-success border-success/20">
        <CheckCircle2 className="mr-1 h-3 w-3" />
        Embedded
      </Badge>
    );
  }

  if (s === "pending" || s === "processing") {
    return (
      <Badge variant="outline" className="bg-warning/10 text-warning border-warning/20">
        <Clock className="mr-1 h-3 w-3" />
        {s === "processing" ? "Processing Vector" : "Pending Vector"}
      </Badge>
    );
  }

  if (s === "failed") {
    return (
      <Badge variant="outline" className="bg-destructive/10 text-destructive border-destructive/20">
        <XCircle className="mr-1 h-3 w-3" />
        Vector Failed
      </Badge>
    );
  }

  return (
    <Badge variant="secondary" className="text-muted-foreground">
      <AlertCircle className="mr-1 h-3 w-3" />
      Unknown Status
    </Badge>
  );
}
