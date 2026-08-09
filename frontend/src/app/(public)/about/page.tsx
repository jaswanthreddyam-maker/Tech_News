import React from "react";
import { Sparkles, Cpu, CpuIcon, ShieldCheck, Zap } from "lucide-react";

export const metadata = {
  title: "About | Tech News Today",
  description: "Learn about Tech News Today autonomous AI newsroom architecture and multi-agent intelligence.",
};

export default function AboutPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-foreground space-y-12">
      <div className="space-y-4 border-b border-border/40 pb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-mono tracking-widest uppercase">
          <Sparkles className="w-3.5 h-3.5" /> Autonomous Intelligence
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
          About Tech News Today
        </h1>
        <p className="text-lg text-muted-foreground max-w-3xl leading-relaxed">
          Tech News Today is an autonomous, multi-agent AI newsroom engineered to scrape, process, evaluate, and deliver real-time technology intelligence without human bottleneck.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-2xl border border-border/50 bg-card/50 space-y-3">
          <Cpu className="w-8 h-8 text-primary" />
          <h3 className="text-lg font-bold">Multi-Agent Ingestion</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Autonomous Celery workers scrape RSS feeds, API streams, and social trends every cycle to capture breakings news instantly.
          </p>
        </div>

        <div className="p-6 rounded-2xl border border-border/50 bg-card/50 space-y-3">
          <Zap className="w-8 h-8 text-amber-400" />
          <h3 className="text-lg font-bold">Neural Ranking & Vector Search</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Advanced vector embedding pipelines score articles based on freshness, novelty, domain authority, and reader preference.
          </p>
        </div>

        <div className="p-6 rounded-2xl border border-border/50 bg-card/50 space-y-3">
          <ShieldCheck className="w-8 h-8 text-emerald-400" />
          <h3 className="text-lg font-bold">Editorial Verification</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            AI evaluators run automated fact-checking, duplicate suppression, and structured summary generation before publication.
          </p>
        </div>
      </div>
    </div>
  );
}
