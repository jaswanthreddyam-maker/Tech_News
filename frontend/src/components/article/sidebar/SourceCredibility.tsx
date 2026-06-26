import React from "react";
import { ExternalLink, ShieldCheck, HelpCircle } from "lucide-react";
import Link from "next/link";

interface SourceCredibilityProps {
  sourceName: string;
  sourceUrl: string | null;
  credibilityScore: string;
  aiConfidence: string;
  publishedAt: string;
}

function getProgressString(scoreStr: string) {
  if (scoreStr === "—") return '░'.repeat(10);
  const score = parseInt(scoreStr, 10);
  if (isNaN(score)) return '░'.repeat(10);
  const filled = Math.round(score / 10);
  return '█'.repeat(filled) + '░'.repeat(10 - filled);
}

export function SourceCredibility({
  sourceName,
  sourceUrl,
  credibilityScore,
  aiConfidence,
  publishedAt
}: SourceCredibilityProps) {

  return (
    <div className="bg-card border border-border rounded-xl p-5 space-y-5">
      <div className="flex items-center gap-2 border-b border-border/50 pb-4">
        <ShieldCheck className="w-4 h-4 text-emerald-500" />
        <h3 className="font-sans font-bold text-sm text-foreground tracking-tight">
          Source Verification
        </h3>
      </div>

      <div className="space-y-4">
        <div className="flex justify-between items-center text-sm">
          <span className="text-muted-foreground">Source</span>
          <div className="flex items-center gap-1 group relative cursor-help">
            <span className="font-bold font-sans text-foreground">{sourceName}</span>
            {sourceName === "—" && (
              <>
                <HelpCircle className="w-3 h-3 text-muted-foreground" />
                  <div className="absolute right-0 bottom-full mb-2 w-max max-w-xs bg-popover border border-border text-xs p-2 rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                  Metadata unavailable
                </div>
              </>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-1 text-sm">
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">Credibility</span>
            <div className="flex items-center gap-1 group relative cursor-help">
              <span className="font-mono">{credibilityScore}</span>
              {credibilityScore === "—" && (
                <>
                  <HelpCircle className="w-3 h-3 text-muted-foreground" />
                    <div className="absolute right-0 bottom-full mb-2 w-max max-w-xs bg-popover border border-border text-xs p-2 rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                    Metadata unavailable
                  </div>
                </>
              )}
            </div>
          </div>
          <div className="text-emerald-500 font-mono text-xs tracking-widest text-right">
            {getProgressString(credibilityScore)}
          </div>
        </div>

        <div className="flex flex-col gap-1 text-sm">
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">AI Confidence</span>
            <div className="flex items-center gap-1 group relative cursor-help">
              <span className="font-mono">{aiConfidence}</span>
              {aiConfidence === "—" && (
                <>
                  <HelpCircle className="w-3 h-3 text-muted-foreground" />
                    <div className="absolute right-0 bottom-full mb-2 w-max max-w-xs bg-popover border border-border text-xs p-2 rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                    Metadata unavailable
                  </div>
                </>
              )}
            </div>
          </div>
          <div className="text-primary font-mono text-xs tracking-widest text-right">
            {getProgressString(aiConfidence)}
          </div>
        </div>

        <div className="flex justify-between items-center text-sm border-t border-border/50 pt-4">
          <span className="text-muted-foreground">Published</span>
          <div className="flex items-center gap-1 group relative cursor-help">
            <span className="text-foreground">{publishedAt}</span>
            {publishedAt === "—" && (
              <>
                <HelpCircle className="w-3 h-3 text-muted-foreground" />
                  <div className="absolute right-0 bottom-full mb-2 w-max max-w-xs bg-popover border border-border text-xs p-2 rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                  Metadata unavailable
                </div>
              </>
            )}
          </div>
        </div>

        {sourceUrl && sourceUrl !== "#" && (
          <div className="pt-2">
            <Link 
              href={sourceUrl} 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center justify-between w-full p-3 rounded-lg bg-card hover:bg-accent/10 transition-colors border border-border group focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
            >
              <span className="text-xs font-mono uppercase tracking-widest text-muted-foreground group-hover:text-foreground transition-colors">
                Original Source
              </span>
              <ExternalLink className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
