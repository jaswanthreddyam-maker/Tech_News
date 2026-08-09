import React from "react";
import { Shield } from "lucide-react";

export const metadata = {
  title: "Privacy Policy | Tech News Today",
  description: "Privacy policy and data protection principles for Tech News Today readers.",
};

export default function PrivacyPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-foreground space-y-10">
      <div className="space-y-4 border-b border-border/40 pb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-mono tracking-widest uppercase">
          <Shield className="w-3.5 h-3.5" /> Privacy First Architecture
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
          Privacy Policy
        </h1>
        <p className="text-muted-foreground">Last updated: August 2026</p>
      </div>

      <div className="prose prose-invert max-w-none space-y-6 text-muted-foreground">
        <section className="space-y-2">
          <h2 className="text-xl font-bold text-foreground">1. Anonymous Telemetry & Preferences</h2>
          <p>
            Tech News Today utilizes local browser storage and anonymous session tokens to deliver personalized news feeds without tracking your personal identity.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-xl font-bold text-foreground">2. Data Security & Storage</h2>
          <p>
            All user preference vectors and reading telemetry are encrypted at rest using PostgreSQL row-level security and stored securely via Supabase.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-xl font-bold text-foreground">3. No Third-Party Tracking</h2>
          <p>
            We do not sell user data, run third-party advertising trackers, or share behavioral profiles with external advertising networks.
          </p>
        </section>
      </div>
    </div>
  );
}
