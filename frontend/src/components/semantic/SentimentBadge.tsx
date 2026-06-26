import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface SentimentBadgeProps {
  sentiment: "positive" | "negative" | "neutral" | string;
  score?: number;
}

export function SentimentBadge({ sentiment, score }: SentimentBadgeProps) {
  const s = sentiment.toLowerCase();
  
  if (s === "positive") {
    return (
      <Badge variant="outline" className="bg-success/10 text-success border-success/20">
        <TrendingUp className="mr-1 h-3 w-3" />
        Positive {score !== undefined && `(${score.toFixed(2)})`}
      </Badge>
    );
  }
  
  if (s === "negative") {
    return (
      <Badge variant="outline" className="bg-destructive/10 text-destructive border-destructive/20">
        <TrendingDown className="mr-1 h-3 w-3" />
        Negative {score !== undefined && `(${score.toFixed(2)})`}
      </Badge>
    );
  }

  return (
    <Badge variant="secondary" className="text-muted-foreground border-border/50">
      <Minus className="mr-1 h-3 w-3" />
      Neutral {score !== undefined && `(${score.toFixed(2)})`}
    </Badge>
  );
}
