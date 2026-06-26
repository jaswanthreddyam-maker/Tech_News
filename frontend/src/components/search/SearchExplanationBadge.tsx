import { Badge } from "@/components/ui/badge";
import { SearchScoreComponent } from "@/lib/api/search/types";

interface Props {
  components: SearchScoreComponent[];
}

export function SearchExplanationBadge({ components }: Props) {
  if (!components || components.length === 0) return null;

  // We only show badges for components that significantly contributed (e.g., > 10% weight or specific types)
  const sorted = [...components].sort((a, b) => b.weighted_score - a.weighted_score);

  const badges = [];

  for (const comp of sorted) {
    if (comp.component === "semantic" && comp.weighted_score > 0.3) {
      badges.push({ label: "Semantic Match", variant: "default" as const });
    } else if (comp.component === "keyword" && comp.weighted_score > 0.2) {
      badges.push({ label: "Keyword Match", variant: "secondary" as const });
    } else if (comp.component === "freshness" && comp.weighted_score > 0.1) {
      badges.push({ label: "Fresh", variant: "outline" as const });
    } else if (comp.component === "credibility" && comp.score > 0.9) {
      badges.push({ label: "Highly Credible", variant: "secondary" as const });
    }
  }

  // Deduplicate badges
  const uniqueBadges = badges.filter((b, index, self) => index === self.findIndex((t) => t.label === b.label));

  if (uniqueBadges.length === 0) {
    // Fallback if no component was high enough, but it matched
    return <Badge variant="outline" className="text-[10px] h-5 tracking-widest uppercase">Match</Badge>;
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {uniqueBadges.map((b) => (
        <Badge key={b.label} variant={b.variant} className="text-[10px] h-5 tracking-widest uppercase">
          {b.label}
        </Badge>
      ))}
    </div>
  );
}
