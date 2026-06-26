"use client";

import { Reveal } from "@/components/animations";

export function PopularSources() {
  const enabled = process.env.NEXT_PUBLIC_FF_TOP_SOURCES === "true";

  if (!enabled) return null;

  return (
    <Reveal>
      <div className="bg-card border border-border p-6 rounded-lg">
        <h3 className="font-sans font-bold mb-4">Top Sources</h3>
        <p className="text-sm text-muted-foreground">Evaluating trust scores...</p>
      </div>
    </Reveal>
  );
}
