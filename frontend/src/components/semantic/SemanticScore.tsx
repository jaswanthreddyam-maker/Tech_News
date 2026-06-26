import * as React from "react";
import { Sparkles } from "lucide-react";

interface SemanticScoreProps {
  score: number;
}

export function SemanticScore({ score }: SemanticScoreProps) {
  // Assuming score is between 0 and 1, where 1 is perfect match
  const percentage = Math.round(score * 100);
  
  let colorClass = "bg-primary text-primary-foreground";
  if (percentage < 50) colorClass = "bg-muted text-muted-foreground";
  else if (percentage < 70) colorClass = "bg-accent text-accent-foreground";
  else if (percentage > 90) colorClass = "bg-success text-success-foreground";

  return (
    <div className="flex items-center gap-2" title={`Semantic similarity: ${percentage}%`}>
      <Sparkles className="h-4 w-4 text-accent" />
      <div className="h-2 w-16 bg-muted rounded-full overflow-hidden">
        <div 
          className={`h-full ${colorClass} transition-all duration-500 ease-out`} 
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-xs font-mono font-medium">{percentage}% match</span>
    </div>
  );
}
