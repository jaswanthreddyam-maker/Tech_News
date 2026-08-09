import React from "react";
import { Terminal, Code, Server, BookOpen } from "lucide-react";

export const metadata = {
  title: "API Documentation | Tech News Today",
  description: "REST API endpoints and realtime SSE event streams documentation for Tech News Today platform.",
};

export default function DocsPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-foreground space-y-12">
      <div className="space-y-4 border-b border-border/40 pb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-400 text-xs font-mono tracking-widest uppercase">
          <Terminal className="w-3.5 h-3.5" /> REST & SSE API v1
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
          API Documentation
        </h1>
        <p className="text-lg text-muted-foreground">
          Integrate live tech intelligence feeds, vector search, and breaking news event streams into your applications.
        </p>
      </div>

      <div className="space-y-8">
        <section className="p-6 rounded-2xl border border-border/50 bg-card/50 space-y-4">
          <div className="flex items-center gap-3">
            <Server className="w-6 h-6 text-primary" />
            <h2 className="text-xl font-bold">1. Base URL</h2>
          </div>
          <p className="text-sm text-muted-foreground">Production REST Endpoint:</p>
          <pre className="p-4 rounded-xl bg-background border border-border font-mono text-sm text-emerald-400 overflow-x-auto">
            https://tech-news-api-production-1b42.up.railway.app/api/v1
          </pre>
        </section>

        <section className="p-6 rounded-2xl border border-border/50 bg-card/50 space-y-4">
          <div className="flex items-center gap-3">
            <Code className="w-6 h-6 text-indigo-400" />
            <h2 className="text-xl font-bold">2. Core Endpoints</h2>
          </div>

          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-background border border-border/60 space-y-2">
              <div className="flex items-center gap-2 font-mono text-xs">
                <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold">GET</span>
                <span className="text-foreground font-semibold">/news?limit=10&sort_by=freshness</span>
              </div>
              <p className="text-xs text-muted-foreground">Fetch canonical processed news articles ordered by freshness or ranking score.</p>
            </div>

            <div className="p-4 rounded-xl bg-background border border-border/60 space-y-2">
              <div className="flex items-center gap-2 font-mono text-xs">
                <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold">GET</span>
                <span className="text-foreground font-semibold">/stories?limit=5</span>
              </div>
              <p className="text-xs text-muted-foreground">Fetch multi-article clustered story timelines with AI synthesized summaries.</p>
            </div>

            <div className="p-4 rounded-xl bg-background border border-border/60 space-y-2">
              <div className="flex items-center gap-2 font-mono text-xs">
                <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-400 font-bold">SSE</span>
                <span className="text-foreground font-semibold">/events/stream</span>
              </div>
              <p className="text-xs text-muted-foreground">Real-time Server-Sent Events stream for autonomous crawler injections and telemetry.</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
