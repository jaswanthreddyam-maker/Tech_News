import { Badge } from "@/components/ui/badge";
import { RecommendationReason } from "@/lib/api/recommendations/types";
import { Sparkles, TrendingUp, ShieldCheck, Tag } from "lucide-react";

interface Props {
  reasons: RecommendationReason[];
  className?: string;
}

export function RecommendationReasonBadges({ reasons, className = "" }: Props) {
  if (!reasons || reasons.length === 0) return null;

  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      {reasons.map((reason, idx) => {
        let Icon = Sparkles;
        let colorClass = "bg-primary/20 text-primary hover:bg-primary/30";

        if (reason.type === "trending") {
          Icon = TrendingUp;
          colorClass = "bg-orange-500/20 text-orange-400 hover:bg-orange-500/30";
        } else if (reason.type === "credible") {
          Icon = ShieldCheck;
          colorClass = "bg-blue-500/20 text-blue-400 hover:bg-blue-500/30";
        } else if (reason.type === "topic") {
          Icon = Tag;
          colorClass = "bg-purple-500/20 text-purple-400 hover:bg-purple-500/30";
        }

        return (
          <Badge key={idx} variant="secondary" className={`font-mono text-[10px] tracking-wider uppercase border-none flex items-center gap-1.5 ${colorClass}`}>
            <Icon className="w-3 h-3" />
            <div className="flex flex-col sm:flex-row sm:items-center sm:gap-1.5 leading-none">
              <span>{reason.label}</span>
              {reason.score && (
                <span className="opacity-70 font-semibold mt-0.5 sm:mt-0">
                  {Math.round(reason.score * 100)}%
                </span>
              )}
            </div>
          </Badge>
        );
      })}
    </div>
  );
}
