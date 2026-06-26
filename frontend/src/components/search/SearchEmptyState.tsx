import { EmptyState, EmptyIllustration, EmptyAction } from "@/components/common/EmptyState";
import { Search } from "lucide-react";

export function SearchEmptyState() {
  const suggestions = [
    "Artificial Intelligence",
    "LLM",
    "GPT",
    "Generative AI"
  ];

  return (
    <EmptyState>
      <EmptyIllustration
        icon={Search}
        title="No results found"
        description="Try another keyword or filter."
      />
      <EmptyAction
        primaryAction={
          <div className="space-y-4 w-full text-center">
            <p className="text-sm font-mono uppercase tracking-wider text-muted-foreground">
              Try Searching For
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {suggestions.map((s) => (
                <button 
                  key={s}
                  className="px-4 py-2 rounded-full border border-border/50 bg-card hover:bg-card/80 transition-colors text-sm text-foreground"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        }
      />
    </EmptyState>
  );
}
