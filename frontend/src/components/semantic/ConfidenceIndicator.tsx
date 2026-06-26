import * as React from "react";
import { Badge } from "@/components/ui/badge";

interface ConfidenceIndicatorProps {
  confidence: number;
}

export function ConfidenceIndicator({ confidence }: ConfidenceIndicatorProps) {
  const percentage = Math.round(confidence * 100);
  let color = "text-success border-success/20 bg-success/10";
  
  if (percentage < 60) color = "text-destructive border-destructive/20 bg-destructive/10";
  else if (percentage < 85) color = "text-warning border-warning/20 bg-warning/10";

  return (
    <Badge variant="outline" className={`${color} font-mono text-xs`}>
      {percentage}% Confidence
    </Badge>
  );
}
