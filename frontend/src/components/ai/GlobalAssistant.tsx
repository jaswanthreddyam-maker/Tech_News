"use client";

import { useState, useEffect, useRef } from "react";
import { m } from "framer-motion";
import { MotionScales } from "@/design-system/motion/tokens";
import ReactMarkdown from "react-markdown";
import { apiClient } from "@/lib/api/client";

interface ToolTrace {
  tool: string;
  args?: any;
}

export function GlobalAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [streamingContent, setStreamingContent] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [toolTraces, setToolTraces] = useState<ToolTrace[]>([]);
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  const [isMounted, setIsMounted] = useState(false);

  // Global hotkey Ctrl+K / Cmd+K
  useEffect(() => {
    setIsMounted(true);
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    if (endOfMessagesRef.current) {
      endOfMessagesRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [streamingContent, toolTraces]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isGenerating) return;

    setIsGenerating(true);
    setStreamingContent("");
    setToolTraces([]);

    try {
      const response = await apiClient.fetchRaw("/assistant/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) return;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n\n");

        for (const line of lines) {
          if (line.startsWith("event: tool_started")) {
            const dataStr = line.replace("event: tool_started\ndata: ", "");
            try {
              const data = JSON.parse(dataStr);
              setToolTraces((prev) => [...prev, { tool: data.tool, args: data.args }]);
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            } catch (err) {}
          } else if (line.startsWith("event: assistant_token")) {
            const dataStr = line.replace("event: assistant_token\ndata: ", "");
            try {
              const data = JSON.parse(dataStr);
              setStreamingContent((prev) => prev + data.text);
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            } catch (err) {}
          } else if (line.startsWith("event: completed")) {
            setIsGenerating(false);
          }
        }
      }
    } catch (e) {
      // eslint-disable-next-line no-console

      setIsGenerating(false);
    }
  };

  if (!isMounted) return null;

  if (!isOpen) {
    return (
      <m.button
        suppressHydrationWarning
        onClick={() => setIsOpen(true)}
        whileHover={{ scale: MotionScales.hover }}
        whileTap={{ scale: MotionScales.tap }}
        className="fixed bottom-6 right-6 w-14 h-14 bg-primary-600 text-white rounded-full shadow-lg hover:bg-primary-700 hover:shadow-xl transition-all flex items-center justify-center z-50 group"
        title="Open Personal Assistant (Cmd+K)"
      >
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        <span className="absolute right-full mr-4 bg-gray-900 text-white text-xs font-mono px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
          Cmd + K
        </span>
      </m.button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-card w-full max-w-3xl h-[85vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200 border border-border">
        
        {/* Header */}
        <div className="p-4 border-b border-border/50 flex items-center justify-between bg-muted/10">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-primary to-primary/80 flex items-center justify-center shadow-inner">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
            </div>
            <div>
              <h2 className="font-bold text-foreground leading-none">Personal Research Assistant</h2>
              <p className="text-xs text-muted-foreground mt-1 font-mono">Personal Research Orchestrator</p>
            </div>
          </div>
          <m.button 
            suppressHydrationWarning
            onClick={() => setIsOpen(false)}
            whileHover={{ scale: MotionScales.hover }}
            whileTap={{ scale: MotionScales.tap }}
            className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted/20 rounded-full transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </m.button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6 bg-background">
          <div className="max-w-2xl mx-auto">
            {toolTraces.length > 0 && (
              <div className="mb-6 bg-card border border-border rounded-lg p-4 shadow-sm font-mono text-xs text-muted-foreground">
                <div className="text-muted-foreground/50 mb-2 uppercase tracking-wider font-semibold text-[10px]">Orchestration Trace</div>
                <ul className="space-y-2">
                  {toolTraces.map((trace, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <svg className="w-4 h-4 text-primary mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                      <div>
                        <span className="font-medium text-foreground">{trace.tool}</span>
                        {trace.args && Object.keys(trace.args).length > 0 && (
                          <span className="ml-2 text-muted-foreground/60">
                            {JSON.stringify(trace.args)}
                          </span>
                        )}
                      </div>
                    </li>
                  ))}
                  {isGenerating && !streamingContent && (
                    <li className="flex items-center gap-2 text-primary animate-pulse">
                      <div className="w-4 h-4 rounded-full border-2 border-primary border-t-transparent animate-spin shrink-0"></div>
                      <span>Thinking...</span>
                    </li>
                  )}
                </ul>
              </div>
            )}

            {streamingContent && (
              <div className="bg-card border border-border rounded-lg p-6 shadow-sm prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown>{streamingContent}</ReactMarkdown>
              </div>
            )}
            <div ref={endOfMessagesRef} />
          </div>
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-border/50 bg-card">
          <form onSubmit={handleSubmit} className="max-w-2xl mx-auto relative flex items-center">
            <input
              suppressHydrationWarning
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask anything (e.g. 'Summarize what I know about NVIDIA')"
              className="w-full pl-4 pr-12 py-4 bg-background border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-shadow text-sm text-foreground placeholder:text-muted-foreground"
              disabled={isGenerating}
            />
            <m.button
              suppressHydrationWarning
              type="submit"
              disabled={isGenerating || !query.trim()}
              whileHover={{ scale: MotionScales.hover }}
              whileTap={{ scale: MotionScales.tap }}
              className="absolute right-2 p-2 bg-primary text-white rounded-lg hover:bg-primary/95 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" /></svg>
            </m.button>
          </form>
        </div>
      </div>
    </div>
  );
}
