"use client";

import { Mail } from "lucide-react";
import { Reveal } from "@/components/animations";

export function Newsletter() {
  return (
    <Reveal>
      <section className="my-16 py-12 px-6 border border-border bg-neutral-950 text-center relative overflow-hidden rounded-2xl">
        <div className="absolute inset-0 bg-primary/5 blur-[100px]" />
        <div className="relative z-10 max-w-xl mx-auto">
          <Mail className="w-8 h-8 text-primary mx-auto mb-4" />
          <h2 className="text-2xl font-serif font-bold text-white mb-2">Daily AI Briefing</h2>
          <p className="text-neutral-400 mb-6 font-mono text-sm">5 minute read. Every morning. No spam.</p>
          <form className="flex gap-2 max-w-md mx-auto">
            <input suppressHydrationWarning type="email" placeholder="agent@network.com" className="flex-1 bg-black border border-neutral-800 rounded-md px-4 py-2 font-mono text-sm focus:outline-none focus:border-primary transition-colors text-white placeholder:text-neutral-500" />
            <button suppressHydrationWarning type="submit" className="bg-white text-black px-6 py-2 font-bold hover:bg-neutral-200 transition-colors rounded-md">
              Subscribe
            </button>
          </form>
        </div>
      </section>
    </Reveal>
  );
}
