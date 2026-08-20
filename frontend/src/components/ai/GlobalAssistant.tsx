"use client";

import { useState, useEffect, useRef } from "react";
import { m, AnimatePresence } from "framer-motion";
import { MotionScales } from "@/design-system/motion/tokens";
import ReactMarkdown from "react-markdown";
import { apiClient } from "@/lib/api/client";
import { AiStarsIcon } from "@/components/common/icons/AiStarsIcon";

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
  const [currentStatusLabel, setCurrentStatusLabel] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  const assistantScrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Focus input on modal open
  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Global hotkey Ctrl+K / Cmd+K & Escape to close
  useEffect(() => {
    setIsMounted(true);
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      } else if (e.key === "Escape" && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  // Auto-scroll on new message content
  useEffect(() => {
    if (assistantScrollRef.current) {
      assistantScrollRef.current.scrollTop = assistantScrollRef.current.scrollHeight;
    }
  }, [messages, currentStatusLabel]);

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsGenerating(false);
    setCurrentStatusLabel(null);
    setMessages((prev) =>
      prev.map((msg) => (msg.status === "streaming" ? { ...msg, status: "complete" } : msg))
    );
  };

  const handleCopyMessage = async (msgId: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(msgId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (e) {
      console.error("Failed to copy message:", e);
    }
  };

  const executeQuery = async (userPrompt: string) => {
    if (!userPrompt.trim() || isGenerating) return;

    setIsGenerating(true);
    setErrorMessage(null);
    setCurrentStatusLabel("Searching research corpus & notes...");

    const tempUserMsgId = `usr_${Date.now()}`;
    const tempAssistantMsgId = `ast_${Date.now()}`;

    // Add user message and initial streaming assistant message to state
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

    let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;

    try {
      const response = await apiClient.fetchRaw("/assistant/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userPrompt, conversation_id: conversationId }),
        timeoutMs: 60000,
        signal: controller.signal,
      });

      reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        setErrorMessage("Failed to read server response stream.");
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

        for (const block of events) {
          const trimmedBlock = block.trim();
          if (!trimmedBlock) continue;

          let eventType = "";
          let dataStr = "";
          for (const rawLine of trimmedBlock.split(/\r?\n/)) {
            const l = rawLine.trim();
            if (l.startsWith("event:")) {
              eventType = l.slice(6).trim();
            } else if (l.startsWith("data:")) {
              dataStr = l.slice(5).trim();
            }
          }

          if (!eventType && trimmedBlock.includes('"event": "error"')) {
            eventType = "error";
          }

          if (eventType === "session") {
            try {
              const data = JSON.parse(dataStr);
              if (data.conversation_id) setConversationId(data.conversation_id);
              if (data.message_id) {
                currentAssistantId = data.message_id;
                setMessages((prev) =>
                  prev.map((msg) => (msg.id === tempAssistantMsgId ? { ...msg, id: data.message_id } : msg))
                );
              }
            } catch (err) {
              console.error("Error parsing session SSE event:", err);
            }
          } else if (eventType === "tool_started") {
            try {
              const data = JSON.parse(dataStr);
              const humanLabel = TOOL_TRANSLATION_MAP[data.tool] || "Searching research corpus...";
              setCurrentStatusLabel(humanLabel);
            } catch (err) {}
          } else if (eventType === "tool_result") {
            setCurrentStatusLabel("Synthesizing response...");
          } else if (eventType === "sources") {
            try {
              const data = JSON.parse(dataStr);
              const targetId = data.message_id || currentAssistantId;
              const sourceCount = data.sources?.length || 0;
              setCurrentStatusLabel(
                sourceCount > 0 ? `Synthesizing answer from ${sourceCount} sources...` : "Synthesizing answer..."
              );
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === targetId ? { ...msg, sources: data.sources } : msg
                )
              );
            } catch (err) {
              console.error("Error parsing sources SSE event:", err);
            }
          } else if (eventType === "assistant_token") {
            setCurrentStatusLabel(null);
            try {
              const data = JSON.parse(dataStr);
              const targetId = data.message_id || currentAssistantId;
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === targetId ? { ...msg, content: msg.content + data.text } : msg
                )
              );
            } catch (err) {
              console.error("Error parsing assistant_token SSE event:", err, "raw data:", dataStr);
            }
          } else if (eventType === "completed") {
            setCurrentStatusLabel(null);
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
            break;
          } else if (eventType === "error") {
            setCurrentStatusLabel(null);
            try {
              const parsed = JSON.parse(dataStr || trimmedBlock);
              const msg = parsed?.data?.message || parsed?.message || "Assistant encountered an error.";
              setErrorMessage(msg);
            } catch (err) {
              setErrorMessage("Assistant encountered an unknown error.");
            }
            setMessages((prev) =>
              prev.map((msg) => (msg.status === "streaming" ? { ...msg, status: "error" } : msg))
            );
            break;
          }
        }
      }
    } catch (e: any) {
      if (e.name !== "AbortError") {
        console.error("Assistant request error:", e);
        const msg = e?.message || "Connection lost or request timed out. Please try again.";
        setErrorMessage(msg);
        setMessages((prev) =>
          prev.map((msg) => (msg.status === "streaming" ? { ...msg, status: "error" } : msg))
        );
      }
    } finally {
      setIsGenerating(false);
      setCurrentStatusLabel(null);
      if (reader) {
        reader.cancel().catch(() => {});
      }
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const promptToSend = query.trim();
    if (!promptToSend) return;
    setQuery("");
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
    setMessages((prev) => prev.filter((m) => m.status !== "error"));
    await executeQuery(lastUserMsg.content);
  };

  if (!isMounted) return null;

  if (!isOpen) {
    return (
      <m.button
        suppressHydrationWarning
        onClick={() => setIsOpen(true)}
        whileHover={{ scale: 1.15 }}
        whileTap={{ scale: 0.92 }}
        className="fixed bottom-6 right-6 p-2 flex items-center justify-center z-50 group focus:outline-none cursor-pointer"
        title="Open Personal Assistant (Cmd+K)"
        aria-label="Open Personal Research Assistant"
      >
        <m.div
          animate={{
            color: [
              "#1e40af", // Dark Blue (Blue-800)
              "#8b5cf6", // Purple (Violet-500)
              "#be123c", // Crimson Red (Rose-700)
              "#1e40af", // Loop back to Dark Blue
            ],
            filter: [
              "drop-shadow(0 0 12px rgba(30, 64, 175, 0.75))",
              "drop-shadow(0 0 16px rgba(139, 92, 246, 0.85))",
              "drop-shadow(0 0 14px rgba(190, 18, 60, 0.75))",
              "drop-shadow(0 0 12px rgba(30, 64, 175, 0.75))",
            ],
          }}
          transition={{
            duration: 6,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className="flex items-center justify-center"
        >
          <AiStarsIcon className="w-10 h-10 transition-transform duration-300 group-hover:scale-110" strokeWidth={2.4} />
        </m.div>
        <span className="absolute right-full mr-4 bg-gray-900/90 backdrop-blur-md text-white text-xs font-mono px-2.5 py-1.5 rounded-lg shadow-md opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap border border-white/10 pointer-events-none">
          Ctrl + K
        </span>
      </m.button>
    );
  }

  return (
    <div 
      role="dialog"
      aria-modal="true"
      aria-label="Personal Research Assistant"
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      {/* Backdrop overlay */}
      <div 
        className="fixed inset-0 bg-black/70 backdrop-blur-md animate-in fade-in duration-150"
        onClick={() => setIsOpen(false)}
        aria-hidden="true"
      />

      {/* Modal Dialog Content */}
      <div className="relative z-10 bg-card w-full max-w-3xl h-[85vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-border">
        
        {/* Header */}
        <div className="px-5 py-4 border-b border-border/60 flex items-center justify-between bg-muted/20 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-primary to-blue-600 flex items-center justify-center shadow-md">
              <AiStarsIcon className="w-5 h-5 text-white" strokeWidth={2.2} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-bold text-foreground leading-none text-base">Personal Research Assistant</h2>
                <span className="text-[10px] uppercase font-semibold font-mono px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
                  Gemini Flash
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">Instant research across personal notes & tech corpus</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="hidden sm:inline-block text-[11px] font-mono text-muted-foreground/60 border border-border/60 rounded px-1.5 py-0.5 bg-background/40">
              ESC to close
            </span>
            <m.button 
              suppressHydrationWarning
              onClick={() => setIsOpen(false)}
              whileHover={{ scale: MotionScales.hover }}
              whileTap={{ scale: MotionScales.tap }}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted/40 rounded-xl transition-colors"
              aria-label="Close Assistant"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </m.button>
          </div>
        </div>

        {/* Content Scroll Area */}
        <div ref={assistantScrollRef} className="flex-1 overflow-y-auto p-6 bg-background space-y-6 scroll-smooth">
          <div className="max-w-2xl mx-auto space-y-6">
            
            {/* Error Banner */}
            {errorMessage && (
              <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-sm flex items-center justify-between shadow-sm">
                <div className="flex items-center gap-2.5">
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
              <div className="py-14 text-center space-y-6">
                <div className="w-14 h-14 rounded-2xl bg-primary/10 text-primary mx-auto flex items-center justify-center border border-primary/20 shadow-inner">
                  <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-lg text-foreground">How can I assist your research today?</h3>
                  <p className="text-sm text-muted-foreground max-w-md mx-auto mt-1">
                    Ask questions about breaking technology, research articles, or topics in your knowledge base.
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
                      className="text-xs px-3.5 py-2 rounded-xl bg-card border border-border/70 hover:border-primary/60 hover:bg-muted/40 text-foreground transition-all hover:shadow-sm"
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Message Thread */}
            {messages.map((msg) => (
              <div key={msg.id} className="space-y-3">
                {msg.role === "user" ? (
                  <div className="flex justify-end">
                    <div className="bg-primary text-white font-medium text-sm px-4 py-2.5 rounded-2xl max-w-[85%] shadow-md leading-relaxed">
                      {msg.content}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="bg-card border border-border rounded-xl p-5 shadow-sm text-foreground text-sm relative group">
                      
                      {/* Copy Message Button */}
                      {msg.content && msg.status !== "streaming" && (
                        <button
                          onClick={() => handleCopyMessage(msg.id, msg.content)}
                          className="absolute top-3 right-3 p-1.5 rounded-lg text-muted-foreground/60 hover:text-foreground hover:bg-muted/50 transition-colors opacity-0 group-hover:opacity-100"
                          title="Copy response markdown"
                        >
                          {copiedId === msg.id ? (
                            <span className="text-[10px] font-medium text-emerald-500 flex items-center gap-1">
                              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                              Copied
                            </span>
                          ) : (
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                          )}
                        </button>
                      )}

                      {/* Content or Skeleton Loading */}
                      {msg.content ? (
                        <div className="prose prose-sm dark:prose-invert max-w-none">
                          <ReactMarkdown components={customMarkdownComponents}>
                            {msg.content}
                          </ReactMarkdown>
                          {msg.status === "streaming" && (
                            <span className="inline-block w-1.5 h-4 bg-primary ml-1 animate-pulse rounded-sm align-middle" />
                          )}
                        </div>
                      ) : (
                        <div className="space-y-3 py-1">
                          {/* Live Status Header */}
                          <div className="flex items-center gap-2 text-xs font-medium text-primary">
                            <div className="w-3.5 h-3.5 rounded-full border-2 border-primary border-t-transparent animate-spin shrink-0" />
                            <AnimatePresence mode="wait">
                              <m.span
                                key={currentStatusLabel || "Synthesizing..."}
                                initial={{ opacity: 0, y: 3 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -3 }}
                                transition={{ duration: 0.15 }}
                              >
                                {currentStatusLabel || "Synthesizing answer..."}
                              </m.span>
                            </AnimatePresence>
                          </div>

                          {/* Shimmer Skeleton Lines */}
                          <div className="space-y-2 pt-1 animate-pulse">
                            <div className="h-3.5 bg-muted/60 rounded-md w-11/12" />
                            <div className="h-3.5 bg-muted/40 rounded-md w-full" />
                            <div className="h-3.5 bg-muted/50 rounded-md w-4/5" />
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Integrated Source Cards */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="space-y-2 pt-1">
                        <div className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground/80 font-semibold pl-1 flex items-center gap-1.5">
                          <svg className="w-3.5 h-3.5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                          </svg>
                          <span>Sources ({msg.sources.length})</span>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {msg.sources.map((src, idx) => (
                            <a
                              key={idx}
                              href={src.url || "#"}
                              target="_blank"
                              rel="noreferrer"
                              className="p-3 rounded-xl bg-card hover:bg-muted/30 border border-border hover:border-primary/40 transition-all text-xs flex flex-col justify-between gap-1.5 group shadow-sm"
                            >
                              <div className="font-medium text-foreground group-hover:text-primary transition-colors line-clamp-1">
                                {src.title}
                              </div>
                              <div className="text-[10px] text-muted-foreground flex items-center justify-between">
                                <span className="truncate max-w-[150px]">{src.source || "Tech News Today"}</span>
                                {src.score !== undefined && (
                                  <span className="font-mono text-primary/80 font-medium px-1.5 py-0.5 rounded bg-primary/10">
                                    {(src.score * 100).toFixed(0)}% match
                                  </span>
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

          </div>
        </div>

        {/* Composer Area */}
        <div className="p-4 border-t border-border/60 bg-card/80 backdrop-blur-sm">
          <form onSubmit={handleSubmit} className="max-w-2xl mx-auto relative flex items-center">
            <input
              ref={inputRef}
              suppressHydrationWarning
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDownInput}
              placeholder="Ask anything across your knowledge and Tech News Today..."
              className="w-full pl-4 pr-24 py-3.5 bg-background border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-shadow text-sm text-foreground placeholder:text-muted-foreground shadow-inner"
              disabled={isGenerating}
            />

            <div className="absolute right-2 flex items-center gap-1.5">
              {isGenerating ? (
                <button
                  type="button"
                  onClick={handleStop}
                  className="px-3.5 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold transition-colors shadow-sm flex items-center gap-1"
                >
                  <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
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
                      ? "bg-primary text-white hover:bg-primary/90 shadow-md cursor-pointer"
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
