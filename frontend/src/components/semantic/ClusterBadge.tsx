import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Network } from "lucide-react";

interface ClusterBadgeProps {
  clusterId: number;
  clusterSize?: number;
}

export function ClusterBadge({ clusterId, clusterSize }: ClusterBadgeProps) {
  return (
    <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20">
      <Network className="mr-1 h-3 w-3" />
      Cluster {clusterId}
      {clusterSize !== undefined && clusterSize > 1 && (
        <span className="ml-1 opacity-70">({clusterSize} stories)</span>
      )}
    </Badge>
  );
}
