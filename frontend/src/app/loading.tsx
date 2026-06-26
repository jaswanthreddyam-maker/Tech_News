import React from "react";

export default function Loading() {
  return (
    <div className="flex flex-col min-h-screen bg-[#080808] text-[#f2f2f2] font-sans">
      {/* Sleek monochromatic status line */}
      <div className="w-full bg-neutral-900 py-2 px-4 text-center font-mono text-[10px] tracking-[0.25em] uppercase font-semibold text-white">
        Syncing with Autonomous Agents...
      </div>

      <header className="border-b border-[#1a1a1a] bg-[#0c0c0c]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div className="animate-pulse">
            <div className="h-10 bg-neutral-900 w-64 mb-2"></div>
            <div className="h-3 bg-neutral-900 w-48"></div>
          </div>
          <div className="h-10 bg-neutral-900 w-48 animate-pulse"></div>
        </div>
      </header>

      <section className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 pt-6">
        <div className="border border-[#1a1a1a] bg-[#0c0c0c] p-5 animate-pulse">
          <div className="h-4 bg-neutral-900 w-1/3 mb-4"></div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="h-16 bg-neutral-900"></div>
            <div className="h-16 bg-neutral-900"></div>
            <div className="h-16 bg-neutral-900"></div>
          </div>
        </div>
      </section>

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col lg:flex-row gap-8">
        <div className="flex-1 space-y-6">
          <div className="h-8 bg-neutral-900 w-1/2 animate-pulse mb-6"></div>
          {[1, 2, 3].map((i) => (
            <div key={i} className="border border-[#1a1a1a] p-6 bg-[#0c0c0c] animate-pulse space-y-4">
              <div className="h-4 bg-neutral-900 w-1/4"></div>
              <div className="h-6 bg-neutral-900 w-3/4"></div>
              <div className="h-4 bg-neutral-900 w-5/6"></div>
              <div className="h-4 bg-neutral-900 w-1/2"></div>
            </div>
          ))}
        </div>

        <aside className="w-full lg:w-80 space-y-6">
          <div className="border border-[#1a1a1a] p-6 bg-[#0c0c0c] animate-pulse space-y-4">
            <div className="h-4 bg-neutral-900 w-1/2"></div>
            <div className="h-3 bg-neutral-900 w-full"></div>
            <div className="h-3 bg-neutral-900 w-5/6"></div>
            <div className="h-3 bg-neutral-900 w-3/4"></div>
          </div>
        </aside>
      </main>
    </div>
  );
}
