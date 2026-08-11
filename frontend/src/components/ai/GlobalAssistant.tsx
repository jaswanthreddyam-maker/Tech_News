"use client";

import { useState, useEffect, useRef } from "react";
import { m, AnimatePresence } from "framer-motion";
import { MotionScales } from "@/design-system/motion/tokens";
import ReactMarkdown from "react-markdown";
import { apiClient } from "@/lib/api/client";

interface SourceItem {
  title: string;
  source?: string;
  url?: string;
  snippet?: string;
  score?: number;
}

interface AssistantMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  status: "complete" | "streaming" | "error";
  sources?: SourceItem[];
  createdAt: string;
}

const TOOL_TRANSLATION_MAP: Record<string, string> = {
  search_global_tech_news: "Searching published Tech News Today...",
  search_my_knowledge: "Searching your research notes...",
  list_workspaces: "Reading workspace index...",
  recent_activity: "Checking recent activity...",
  read_digests: "Reading daily digests...",
  read_note: "Fetching workspace note...",
};

const SUGGESTION_CHIPS = [
  "What happened with NVIDIA recently?",
  "Search my knowledge about AI agents",
  "What did I save about machine learning?",
];

const ROTATING_STATUS_SEQUENCE = [
  "Thinking...",
  "Researching...",
  "Musing...",
  "Connecting the dots...",
  "Polishing response...",
  "Refining the answer...",
  "Almost there...",
  "Finalizing...",
];

const customMarkdownComponents = {
  h1: ({ children }: any) => (
    <h1 className="text-base font-bold text-foreground mt-4 mb-2 border-b border-border/40 pb-1">{children}</h1>
  ),
  h2: ({ children }: any) => (
    <h2 className="text-sm font-bold text-foreground mt-3.5 mb-1.5 border-b border-border/30 pb-1">{children}</h2>
  ),
  h3: ({ children }: any) => (
    <h3 className="text-xs font-semibold text-foreground mt-3 mb-1">{children}</h3>
  ),
  p: ({ children }: any) => (
    <p className="leading-relaxed mb-2.5 last:mb-0 text-foreground text-sm">{children}</p>
  ),
  ul: ({ children }: any) => (
    <ul className="list-disc list-outside space-y-1.5 my-2.5 pl-5 text-foreground text-sm">{children}</ul>
  ),
  ol: ({ children }: any) => (
    <ol className="list-decimal list-outside space-y-1.5 my-2.5 pl-5 text-foreground text-sm">{children}</ol>
  ),
  li: ({ children }: any) => (
    <li className="leading-relaxed">{children}</li>
  ),
  strong: ({ children }: any) => (
    <strong className="font-semibold text-foreground">{children}</strong>
  ),
  table: ({ children }: any) => (
    <div className="overflow-x-auto my-3 border border-border/70 rounded-xl shadow-sm bg-card">
      <table className="w-full text-xs text-left border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }: any) => (
    <thead className="bg-muted/60 border-b border-border/60 font-semibold text-foreground">{children}</thead>
  ),
  tbody: ({ children }: any) => (
    <tbody className="divide-y divide-border/40">{children}</tbody>
  ),
  tr: ({ children }: any) => (
    <tr className="hover:bg-muted/20 transition-colors">{children}</tr>
  ),
  th: ({ children }: any) => (
    <th className="px-3.5 py-2.5 border-r border-border/40 last:border-r-0 font-semibold text-foreground">{children}</th>
  ),
  td: ({ children }: any) => (
    <td className="px-3.5 py-2.5 border-r border-border/40 last:border-r-0 text-foreground/90">{children}</td>
  ),
  a: ({ href, children }: any) => (
    <a href={href} target="_blank" rel="noreferrer" className="text-primary underline hover:text-primary/80 font-medium">
      {children}
    </a>
  ),
};

export function GlobalAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeToolLabel, setActiveToolLabel] = useState<string | null>(null);
  const [statusIndex, setStatusIndex] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  const endOfMessagesRef = useRef<HTMLDivElement>(null);
  const assistantScrollRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const rotationTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopStatusRotation = () => {
    if (rotationTimerRef.current) {
      clearInterval(rotationTimerRef.current);
      rotationTimerRef.current = null;
    }
  };

  const startStatusRotation = () => {
    stopStatusRotation();
    setStatusIndex(0);
    rotationTimerRef.current = setInterval(() => {
      setStatusIndex((prev) => (prev + 1) % ROTATING_STATUS_SEQUENCE.length);
    }, 5000);
  };

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
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      stopStatusRotation();
    };
  }, []);

  // Auto-scroll on new message content
  useEffect(() => {
    if (assistantScrollRef.current) {
      assistantScrollRef.current.scrollTop = assistantScrollRef.current.scrollHeight;
    }
  }, [messages, activeToolLabel, statusIndex]);

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    stopStatusRotation();
    setIsGenerating(false);
    setActiveToolLabel(null);
    setMessages((prev) =>
      prev.map((msg) => (msg.status === "streaming" ? { ...msg, status: "complete" } : msg))
    );
  };

  const executeQuery = async (userPrompt: string) => {
    if (!userPrompt.trim() || isGenerating) return;

    setIsGenerating(true);
    setErrorMessage(null);
    setActiveToolLabel(null);
    startStatusRotation();

    const tempUserMsgId = `usr_${Date.now()}`;
    const tempAssistantMsgId = `ast_${Date.now()}`;

    // Add user message and initial streaming assistant message to state if not retrying
    setMessages((prev) => {
      const lastMsg = prev[prev.length - 1];
      if (lastMsg && lastMsg.role === "user" && lastMsg.content === userPrompt) {
        return [
          ...prev,
          { id: tempAssistantMsgId, role: "assistant", content: "", status: "streaming", createdAt: new Date().toISOString() },
        ];
      }
      return [
        ...prev,
        { id: tempUserMsgId, role: "user", content: userPrompt, status: "complete", createdAt: new Date().toISOString() },
        { id: tempAssistantMsgId, role: "assistant", content: "", status: "streaming", createdAt: new Date().toISOString() },
      ];
    });

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await apiClient.fetchRaw("/assistant/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userPrompt, conversation_id: conversationId }),
        timeoutMs: 60000,
        signal: controller.signal,
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        setErrorMessage("Failed to read server response stream.");
        stopStatusRotation();
        setIsGenerating(false);
        return;
      }

      let currentAssistantId = tempAssistantMsgId;
      let sseBuffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        sseBuffer += decoder.decode(value, { stream: true });
        const events = sseBuffer.split("\n\n");
        sseBuffer = events.pop() || "";

        for (const line of events) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          if (trimmed.startsWith("event: session")) {
            const dataStr = trimmed.replace("event: session\ndata: ", "");
            try {
              const data = JSON.parse(dataStr);
              if (data.conversation_id) setConversationId(data.conversation_id);
              if (data.message_id) {
                currentAssistantId = data.message_id;
                setMessages((prev) =>
                  prev.map((msg) => (msg.id === tempAssistantMsgId ? { ...msg, id: data.message_id } : msg))
                );
              }
            } catch (err) {}
          } else if (trimmed.startsWith("event: tool_started")) {
            const dataStr = trimmed.replace("event: tool_started\ndata: ", "");
            try {
              const data = JSON.parse(dataStr);
              const humanLabel = TOOL_TRANSLATION_MAP[data.tool] || "Searching research corpus...";
              setActiveToolLabel(humanLabel);
            } catch (err) {}
          } else if (trimmed.startsWith("event: tool_result")) {
            setActiveToolLabel(null);
          } else if (trimmed.startsWith("event: sources")) {
            const dataStr = trimmed.replace("event: sources\ndata: ", "");
            try {
              const data = JSON.parse(dataStr);
              const targetId = data.message_id || currentAssistantId;
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === targetId ? { ...msg, sources: data.sources } : msg
                )
              );
            } catch (err) {}
          } else if (trimmed.startsWith("event: assistant_token")) {
            // First token arrives: IMMEDIATELY stop rotating progress labels
            stopStatusRotation();
            const dataStr = trimmed.replace("event: assistant_token\ndata: ", "");
            try {
              const data = JSON.parse(dataStr);
              const targetId = data.message_id || currentAssistantId;
              setActiveToolLabel(null);
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === targetId ? { ...msg, content: msg.content + data.text } : msg
                )
              );
            } catch (err) {}
          } else if (trimmed.startsWith("event: completed")) {
            stopStatusRotation();
            const dataStr = trimmed.replace("event: completed\ndata: ", "");
            try {
              const data = JSON.parse(dataStr);
              const targetId = data.message_id || currentAssistantId;
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === targetId
                    ? {
                        ...msg,
                        content: msg.content || "I couldn't find recent coverage for that query in the Tech News Today corpus.",
                        status: "complete",
                      }
                    : msg
                )
              );
            } catch (err) {}
            setIsGenerating(false);
            setActiveToolLabel(null);
          } else if (trimmed.startsWith("event: error") || trimmed.includes('"event": "error"')) {
            stopStatusRotation();
            try {
              const jsonStr = trimmed.startsWith("event: error")
                ? trimmed.replace("event: error\ndata: ", "")
                : trimmed.replace(/^data:\s*/, "");
              const parsed = JSON.parse(jsonStr);
              const msg = parsed?.data?.message || parsed?.message || "Assistant encountered an error.";
              setErrorMessage(msg);
            } catch (err) {
              setErrorMessage("Assistant encountered an unknown error.");
            }
            setMessages((prev) =>
              prev.map((msg) => (msg.status === "streaming" ? { ...msg, status: "error" } : msg))
            );
            setIsGenerating(false);
            setActiveToolLabel(null);
          }
        }
      }
    } catch (e: any) {
      stopStatusRotation();
      if (e.name !== "AbortError") {
        console.error("Assistant request error:", e);
        const msg = e?.message || "Connection lost or request timed out. Please try again.";
        setErrorMessage(msg);
        setMessages((prev) =>
          prev.map((msg) => (msg.status === "streaming" ? { ...msg, status: "error" } : msg))
        );
      }
      setIsGenerating(false);
      setActiveToolLabel(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const promptToSend = query.trim();
    if (!promptToSend) return;
    setQuery(""); // CLEAR COMPOSER IMMEDIATELY
    await executeQuery(promptToSend);
  };

  const handleKeyDownInput = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleRetry = async () => {
    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
    if (!lastUserMsg) return;
    // Remove failing assistant message
    setMessages((prev) => prev.filter((m) => m.status !== "error"));
    await executeQuery(lastUserMsg.content);
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
        <div ref={assistantScrollRef} className="flex-1 overflow-y-auto p-6 bg-background space-y-6">
          <div className="max-w-2xl mx-auto space-y-6">
            
            {/* Error Banner */}
            {errorMessage && (
              <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-sm flex items-center justify-between shadow-sm">
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>{errorMessage}</span>
                </div>
                <div className="flex items-center gap-3">
                  <button 
                    onClick={handleRetry} 
                    className="text-xs font-semibold underline hover:no-underline text-red-600 dark:text-red-400"
                  >
                    Retry
                  </button>
                  <button 
                    onClick={() => setErrorMessage(null)} 
                    className="text-xs text-muted-foreground hover:text-foreground"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            )}

            {/* Empty State */}
            {messages.length === 0 && (
              <div className="py-12 text-center space-y-6">
                <div className="w-12 h-12 rounded-2xl bg-primary/10 text-primary mx-auto flex items-center justify-center">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                </div>
                <div>
                  <h3 className="font-semibold text-lg text-foreground">Personal Research Assistant</h3>
                  <p className="text-sm text-muted-foreground max-w-md mx-auto mt-1">
                    Research anything across your personal knowledge base and Tech News Today.
                  </p>
                </div>
                <div className="flex flex-wrap justify-center gap-2 pt-2">
                  {SUGGESTION_CHIPS.map((chip, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setQuery("");
                        executeQuery(chip);
                      }}
                      className="text-xs px-3 py-2 rounded-xl bg-card border border-border/60 hover:border-primary/50 text-foreground transition-all hover:shadow-sm"
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Message Stream Thread */}
            {messages.map((msg) => (
              <div key={msg.id} className="space-y-3">
                {msg.role === "user" ? (
                  <div className="flex justify-end">
                    <div className="bg-blue-600 text-white font-medium text-sm px-4 py-2.5 rounded-2xl max-w-[85%] shadow-md">
                      {msg.content}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="bg-card border border-border rounded-xl p-5 shadow-sm text-foreground text-sm prose prose-sm dark:prose-invert max-w-none">
                      {msg.content ? (
                        <ReactMarkdown components={customMarkdownComponents}>
                          {msg.content}
                        </ReactMarkdown>
                      ) : (
                        <div className="flex items-center gap-2 text-muted-foreground font-mono text-xs h-5 overflow-hidden">
                          <div className="w-3.5 h-3.5 rounded-full border-2 border-primary border-t-transparent animate-spin shrink-0"></div>
                          <AnimatePresence mode="wait">
                            <m.span
                              key={activeToolLabel || ROTATING_STATUS_SEQUENCE[statusIndex]}
                              initial={{ opacity: 0, y: 4 }}
                              animate={{ opacity: 1, y: 0 }}
                              exit={{ opacity: 0, y: -4 }}
                              transition={{ duration: 0.2 }}
                              className="inline-block"
                            >
                              {activeToolLabel || ROTATING_STATUS_SEQUENCE[statusIndex]}
                            </m.span>
                          </AnimatePresence>
                        </div>
                      )}
                    </div>

                    {/* Source Cards */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="space-y-2 pt-1">
                        <div className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground/70 font-semibold pl-1">
                          Sources ({msg.sources.length})
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {msg.sources.map((src, idx) => (
                            <a
                              key={idx}
                              href={src.url || "#"}
                              target="_blank"
                              rel="noreferrer"
                              className="p-3 rounded-lg bg-card/60 hover:bg-card border border-border/50 hover:border-primary/40 transition-all text-xs flex flex-col justify-between gap-1 group"
                            >
                              <div className="font-medium text-foreground group-hover:text-primary transition-colors line-clamp-1">
                                {src.title}
                              </div>
                              <div className="text-[10px] text-muted-foreground flex items-center justify-between">
                                <span>{src.source || "Tech News Today"}</span>
                                {src.score && (
                                  <span className="font-mono">{(src.score * 100).toFixed(0)}% match</span>
                                )}
                              </div>
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}

            {/* Transient Tool Execution Indicator */}
            {activeToolLabel && (
              <div className="flex items-center gap-2 text-xs font-mono text-primary bg-primary/5 border border-primary/20 rounded-lg p-3 animate-pulse">
                <div className="w-3.5 h-3.5 rounded-full border-2 border-primary border-t-transparent animate-spin shrink-0"></div>
                <span>{activeToolLabel}</span>
              </div>
            )}

            <div ref={endOfMessagesRef} />
          </div>
        </div>

        {/* Composer Area */}
        <div className="p-4 border-t border-border/50 bg-card">
          <form onSubmit={handleSubmit} className="max-w-2xl mx-auto relative flex items-center">
            <input
              suppressHydrationWarning
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDownInput}
              placeholder="Ask anything across your knowledge and Tech News Today..."
              className="w-full pl-4 pr-24 py-3.5 bg-background border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-shadow text-sm text-foreground placeholder:text-muted-foreground"
              disabled={isGenerating}
            />

            <div className="absolute right-2 flex items-center gap-1.5">
              {isGenerating ? (
                <button
                  type="button"
                  onClick={handleStop}
                  className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-medium transition-colors shadow-sm"
                >
                  Stop
                </button>
              ) : (
                <m.button
                  suppressHydrationWarning
                  type="submit"
                  disabled={!query.trim()}
                  whileHover={query.trim() ? { scale: MotionScales.hover } : undefined}
                  whileTap={query.trim() ? { scale: MotionScales.tap } : undefined}
                  className={`p-2.5 rounded-xl transition-all flex items-center justify-center ${
                    query.trim()
                      ? "bg-blue-600 text-white hover:bg-blue-500 shadow-md cursor-pointer"
                      : "bg-muted/60 text-muted-foreground/40 border border-border/50 cursor-not-allowed"
                  }`}
                  title={query.trim() ? "Send message (Enter)" : "Type a message to send"}
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                  </svg>
                </m.button>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
