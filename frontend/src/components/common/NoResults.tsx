// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { Search, Frown } from "lucide-react";
import { ReactNode } from "react";

interface Props {
  query?: string;
  suggestions?: string[];
  action?: ReactNode;
  className?: string;
}

export function NoResults({ query, suggestions = [], action, className = "" }: Props) {
  return (
    <div className={`flex flex-col items-center justify-center py-24 text-center px-4 ${className}`}>
      <div className="w-16 h-16 rounded-full bg-neutral-900 flex items-center justify-center mb-6">
        <Search className="w-8 h-8 text-muted-foreground opacity-50" />
      </div>
      
      <h3 className="text-xl font-bold mb-2">
        {query ? `No results for "${query}"` : "No matches found"}
      </h3>
      <p className="text-muted-foreground max-w-md mx-auto mb-8">
        We couldn&apos;t find anything matching your current filters or query.
      </p>

      {suggestions.length > 0 && (
        <div className="space-y-4 mb-8">
          <p className="text-sm font-mono uppercase tracking-wider text-muted-foreground">
            Try Searching For
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {suggestions.map((s) => (
              <button 
                key={s}
                className="px-4 py-2 rounded-full border border-border/50 bg-card hover:bg-card/80 transition-colors text-sm"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {action && (
        <div className="mt-4">
          {action}
        </div>
      )}
    </div>
  );
}
