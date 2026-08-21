import React, { useState, useEffect, useRef } from 'react';
import { m } from 'framer-motion';
import { MotionScales } from '@/design-system/motion/tokens';
import { useConversation, ConversationMode, Citation, ChatMessage } from '@/hooks/useConversation';
import ReactMarkdown from 'react-markdown';
import { Skeleton } from '@/design-system/components/Skeleton';
import { useLoadingState } from '@/design-system/hooks/useLoadingState';
import { EmptyState, EmptyIllustration } from '@/components/common/EmptyState';
import { MessageCircle } from 'lucide-react';
import Link from 'next/link';
import { ArticleLink } from "@/domains/article/ArticleLink";
import { useAuthGate } from '@/hooks/useAuthGate';
import { FeatureCapability } from '@/lib/auth/features';

interface ConversationalSearchProps {
  conversationId: string | null;
  initialMode?: ConversationMode;
  articleId?: number;
  articleTitle?: string;
  keywords?: string[];
  className?: string;
  hideModeSelector?: boolean;
  showOpenFullChat?: boolean;
  workspaceId?: number;
}

const EvidenceBadge: React.FC<{ evidence?: any }> = () => null;

export const ConversationalSearch: React.FC<ConversationalSearchProps> = ({
  conversationId,
  initialMode = 'GENERAL',
  articleId,
  articleTitle,
  keywords = [],
  className = '',
  hideModeSelector = false,
  showOpenFullChat = false,
}) => {
  const { requireAuthentication } = useAuthGate();
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { messages, isLoading, mode, title, setMode, sendMessage, stopGeneration, capabilityError, checkCapability } =
    useConversation(conversationId, initialMode, articleId);

  const [input, setInput] = useState('');
  const [showComparePanel, setShowComparePanel] = useState(false);
  const [contextA, setContextA] = useState('');
  const [contextB, setContextB] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatScrollRef = useRef<HTMLDivElement>(null);
  
  const loadingLevel = useLoadingState(isLoading);

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!requireAuthentication(FeatureCapability.AI_ARTICLE_CHAT)) {
      return;
    }
    if (input.trim() && !isLoading) {
      sendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleFollowUp = (question: string) => {
    if (!requireAuthentication(FeatureCapability.AI_ARTICLE_CHAT)) {
      return;
    }
    sendMessage(question);
  };

  const handleCompareSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!requireAuthentication(FeatureCapability.AI_ARTICLE_CHAT)) {
      return;
    }
    if (contextA.trim() && contextB.trim() && !isLoading) {
      const originalMode = mode;
      setMode('COMPARISON');
      sendMessage(`Compare ${contextA} vs ${contextB}`, 
        { type: 'query', value: contextA }, 
        { type: 'query', value: contextB }
      ).then(() => {
        setMode(originalMode); // revert after sending
      });
      setShowComparePanel(false);
      setContextA('');
      setContextB('');
    }
  };

  const confidenceColor = (level?: string) => {
    switch (level) {
      case 'High':
        return 'text-emerald-500 bg-emerald-500/10';
      case 'Medium':
        return 'text-amber-500 bg-amber-500/10';
      case 'Low':
        return 'text-red-500 bg-red-500/10';
      default:
        return 'text-muted-foreground bg-muted';
    }
  };

  return (
    <div
      className={`flex flex-col h-full max-h-[800px] border border-border/80 rounded-xl overflow-hidden bg-card shadow-sm ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border/50 bg-muted/20">
        <div>
          <h3 className="font-semibold text-foreground">
            {mode === 'ARTICLE' ? 'Ask about this article' : 'Ask AI'}
          </h3>
          {mode === 'ARTICLE' && (
            <p className="text-xs text-muted-foreground mt-0.5">
              Answers are grounded in this article and related coverage.
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {!hideModeSelector && (
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as ConversationMode)}
              className="text-sm border-border rounded-md shadow-sm bg-background text-foreground focus:border-primary focus:ring-primary"
              disabled={isLoading}
            >
              <option value="GENERAL">General Search</option>
              <option value="ARTICLE">Reading Assistant</option>
              <option value="ELI15">Explain Like I&apos;m 15</option>
              <option value="COMPARISON">Compare Topics</option>
              <option value="TIMELINE">Generate Timeline</option>
              <option value="TOPIC">Explore Topic</option>
            </select>
          )}
          {showOpenFullChat && conversationId && (
            <Link
              href={`/chat?id=${conversationId}`}
              className="text-xs text-primary hover:text-primary/90 font-medium whitespace-nowrap"
            >
              Open Full Chat →
            </Link>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div ref={chatScrollRef} className="flex-1 p-4 overflow-y-auto space-y-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full space-y-4">
            <EmptyState>
              <EmptyIllustration
                icon={MessageCircle}
                title={mode === 'ARTICLE' ? 'Ask about this article' : 'Ask AI'}
                description={mode === 'ARTICLE'
                  ? 'Ask any question about this article to get more context, simple explanations, or technical details.'
                  : "Ask any question about tech news, and I'll search our articles to find the answer."}
              />
            </EmptyState>
            <div className="flex flex-wrap justify-center gap-2 mt-4">
              {mode === 'ARTICLE' ? (
                <>
                  <m.button
                    onClick={() => sendMessage('Explain this article in simpler terms.')}
                    whileHover={{ scale: MotionScales.hover }}
                    whileTap={{ scale: MotionScales.tap }}
                    className="px-3 py-1.5 text-xs bg-secondary hover:bg-secondary/80 rounded-full transition-colors text-secondary-foreground"
                  >
                    Explain simply
                  </m.button>
                  <m.button
                    onClick={() => sendMessage('What are the biggest takeaways?')}
                    whileHover={{ scale: MotionScales.hover }}
                    whileTap={{ scale: MotionScales.tap }}
                    className="px-3 py-1.5 text-xs bg-secondary hover:bg-secondary/80 rounded-full transition-colors text-secondary-foreground"
                  >
                    Key takeaways
                  </m.button>
                  <m.button
                    onClick={() => sendMessage('Why does this matter?')}
                    whileHover={{ scale: MotionScales.hover }}
                    whileTap={{ scale: MotionScales.tap }}
                    className="px-3 py-1.5 text-xs bg-secondary hover:bg-secondary/80 rounded-full transition-colors text-secondary-foreground"
                  >
                    Why it matters
                  </m.button>
                  <m.button
                    onClick={() => sendMessage('Summarize the technical details.')}
                    whileHover={{ scale: MotionScales.hover }}
                    whileTap={{ scale: MotionScales.tap }}
                    className="px-3 py-1.5 text-xs bg-secondary hover:bg-secondary/80 rounded-full transition-colors text-secondary-foreground"
                  >
                    Technical details
                  </m.button>
                </>
              ) : (
                <>
                  <m.button
                    onClick={() => sendMessage('What are the latest developments in AI?')}
                    whileHover={{ scale: MotionScales.hover }}
                    whileTap={{ scale: MotionScales.tap }}
                    className="px-3 py-1.5 text-xs bg-secondary hover:bg-secondary/80 rounded-full transition-colors text-secondary-foreground"
                  >
                    Latest AI news
                  </m.button>
                  <m.button
                    onClick={() => setShowComparePanel(true)}
                    whileHover={{ scale: MotionScales.hover }}
                    whileTap={{ scale: MotionScales.tap }}
                    className="px-3 py-1.5 text-xs bg-primary/10 text-primary hover:bg-primary/20 rounded-full transition-colors font-medium border border-primary/20"
                  >
                    Compare Topics
                  </m.button>
                </>
              )}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id}>
              <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] rounded-2xl px-5 py-4 ${
                    msg.role === 'user'
                      ? 'bg-primary text-primary-foreground rounded-br-sm'
                      : 'bg-zinc-100 text-zinc-950 rounded-bl-sm border border-zinc-300 shadow-md'
                  }`}
                >
                  {/* Searching state */}
                  {msg.role === 'assistant' && msg.status === 'searching' && (
                    <div className="flex items-center space-x-2 text-sm text-zinc-600 animate-pulse">
                      <svg
                        className="w-4 h-4 animate-spin"
                        viewBox="0 0 24 24"
                        fill="none"
                      >
                        <path
                          d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                      <span>Searching articles...</span>
                    </div>
                  )}

                  {/* Generating state (no tokens yet) */}
                  {msg.role === 'assistant' &&
                    msg.status === 'generating' &&
                    msg.content === '' && (
                      <div className="space-y-2.5 mt-1">
                        <Skeleton level={loadingLevel} className="h-4 w-3/4" />
                        <Skeleton level={loadingLevel} className="h-4 w-1/2" />
                        <div className="flex items-center gap-2 pt-1 text-xs text-zinc-600">
                          <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                            <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                          </svg>
                          <span>Synthesizing response...</span>
                        </div>
                      </div>
                    )}

                  {/* Provenance Badge */}
                  {msg.role === 'assistant' && msg.evidence && (
                    <EvidenceBadge evidence={msg.evidence} />
                  )}

                  {/* Message content */}
                  <div
                    className={`prose prose-sm max-w-none ${
                      msg.role === 'user'
                        ? 'prose-invert text-primary-foreground'
                        : 'text-zinc-950 font-normal prose-headings:text-zinc-950 prose-p:text-zinc-950 prose-p:leading-relaxed prose-strong:text-zinc-950 prose-strong:font-bold prose-li:text-zinc-950 prose-code:text-zinc-950 prose-a:text-indigo-600'
                    }`}
                  >
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>

                  {/* Error state */}
                  {msg.status === 'error' && (
                    <div className="mt-2 text-xs text-red-500 flex items-center">
                      <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      Generation failed. Please try again.
                    </div>
                  )}
                </div>
              </div>

              {/* Comparison Metadata Cards (displayed before/above standard citations if present) */}
              {msg.comparisonMetadata && (
                <div className="ml-2 mt-3 flex gap-3 max-w-[85%]">
                  <div className="flex-1 bg-card border border-border/60 rounded-lg p-3 shadow-sm">
                    <div className="text-[10px] font-semibold text-muted-foreground/60 uppercase tracking-wider mb-1">Context A</div>
                    <div className="font-medium text-sm text-foreground truncate">{msg.comparisonMetadata.context_a.name}</div>
                    <div className="text-xs text-primary mt-1 flex items-center gap-1">
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                      {msg.comparisonMetadata.context_a.sources} sources
                    </div>
                  </div>
                  <div className="flex-1 bg-card border border-border/60 rounded-lg p-3 shadow-sm">
                    <div className="text-[10px] font-semibold text-muted-foreground/60 uppercase tracking-wider mb-1">Context B</div>
                    <div className="font-medium text-sm text-foreground truncate">{msg.comparisonMetadata.context_b.name}</div>
                    <div className="text-xs text-primary mt-1 flex items-center gap-1">
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                      {msg.comparisonMetadata.context_b.sources} sources
                    </div>
                  </div>
                </div>
              )}

              {/* Sources Panel (below assistant messages) */}
              {msg.role === 'assistant' &&
                msg.status === 'completed' &&
                msg.citations &&
                msg.citations.length > 0 && (
                  <div className="ml-2 mt-3 p-3 bg-muted/20 rounded-lg border border-border/40 max-w-[85%]">
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                      Sources Used
                    </p>
                    <div className="space-y-1.5">
                      {msg.citations.map((cit, idx) => (
                        <div key={idx} className="flex items-center justify-between text-xs">
                          <ArticleLink
                            article={{ id: cit.article_id, slug: String(cit.article_id), title: cit.title } as any}
                            section="AIChatCitation"
                            className="text-primary hover:underline truncate max-w-[70%]"
                          >
                            [{idx + 1}] {cit.title}
                          </ArticleLink>
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${confidenceColor(
                              cit.confidence
                            )}`}
                          >
                            {cit.confidence || 'N/A'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              {/* Follow-up suggestions (below the last completed assistant message) */}
              {msg.role === 'assistant' &&
                msg.status === 'completed' &&
                msg.followUps &&
                msg.followUps.length > 0 && (
                  <div className="ml-2 mt-3 flex flex-wrap gap-2 max-w-[85%]">
                    {msg.followUps.map((q, idx) => (
                      <m.button
                        key={idx}
                        onClick={() => handleFollowUp(q)}
                        disabled={isLoading}
                        whileHover={{ scale: MotionScales.hover }}
                        whileTap={{ scale: MotionScales.tap }}
                        className="px-3 py-1.5 text-xs text-primary bg-primary/10 hover:bg-primary/20 border border-primary/20 rounded-full transition-colors disabled:opacity-50 text-left"
                      >
                        {q}
                      </m.button>
                    ))}
                  </div>
                )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-card border-t border-border/60 flex flex-col gap-2">
        {/* Smart Suggestions for Articles */}
        {mode === 'ARTICLE' && messages.length === 0 && keywords.length > 0 && (
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
            <span className="text-xs text-muted-foreground/60 py-1.5 shrink-0">Compare with:</span>
            {keywords.slice(0, 3).map((kw, i) => (
              <m.button
                key={i}
                onClick={() => {
                  if (!requireAuthentication(FeatureCapability.AI_ARTICLE_CHAT)) {
                    return;
                  }
                  setContextA(articleTitle || 'This Article');
                  setContextB(kw);
                  setShowComparePanel(true);
                }}
                whileHover={{ scale: MotionScales.hover }}
                whileTap={{ scale: MotionScales.tap }}
                className="px-3 py-1 text-xs text-primary bg-primary/10 hover:bg-primary/20 border border-primary/20 rounded-full shrink-0 transition-colors"
              >
                {kw}
              </m.button>
            ))}
          </div>
        )}

        {capabilityError ? (
          <div className="flex flex-col items-center justify-center p-4 text-center space-y-3 bg-destructive/5 border border-destructive/20 rounded-xl">
            <div className="flex items-center gap-2 text-destructive font-medium text-sm">
              <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span>
                {capabilityError === 'OFFLINE' && 'AI Assistant Offline'}
                {capabilityError === 'UNAUTHORIZED' && 'Authentication Required'}
                {capabilityError === 'STREAM_UNSUPPORTED' && 'Browser Incompatible'}
                {capabilityError === 'RATE_LIMITED' && 'Rate Limit Reached'}
              </span>
            </div>
            <p className="text-xs text-muted-foreground max-w-sm">
              {capabilityError === 'OFFLINE' && 'Failed to connect to the AI service. Please check your network connectivity.'}
              {capabilityError === 'UNAUTHORIZED' && 'You must be signed in to converse with the autonomous AI assistant.'}
              {capabilityError === 'STREAM_UNSUPPORTED' && 'Your current browser does not support readable streams. Try using Chrome, Firefox, or Safari.'}
              {capabilityError === 'RATE_LIMITED' && 'You have sent too many requests. Please wait a moment before trying again.'}
            </p>
            {capabilityError === 'UNAUTHORIZED' ? (
              <Link href="/login">
                <button className="px-3 py-1.5 text-xs font-semibold text-primary-foreground bg-primary hover:bg-primary/90 rounded-lg transition-colors shadow-sm">
                  Sign In
                </button>
              </Link>
            ) : capabilityError !== 'STREAM_UNSUPPORTED' ? (
              <button
                onClick={() => checkCapability()}
                className="px-3 py-1.5 text-xs font-semibold text-foreground bg-muted hover:bg-muted/80 rounded-lg transition-colors border border-border"
              >
                Retry Connection
              </button>
            ) : null}
          </div>
        ) : showComparePanel ? (
          <form onSubmit={handleCompareSubmit} className="bg-muted/10 border border-border/60 rounded-xl p-3 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Compare Topics</span>
              <button type="button" onClick={() => setShowComparePanel(false)} className="text-muted-foreground/60 hover:text-foreground">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="flex gap-2">
              <input 
                type="text" 
                placeholder="Context A (e.g., OpenAI)" 
                value={contextA} 
                onChange={(e) => setContextA(e.target.value)}
                className="flex-1 px-3 py-2 text-sm bg-background border border-border rounded-lg focus:ring-2 focus:ring-primary outline-none text-foreground"
                aria-required="true"
              />
              <div className="flex items-center justify-center px-2 text-xs font-medium text-muted-foreground/60">VS</div>
              <input 
                type="text" 
                placeholder="Context B (e.g., Anthropic)" 
                value={contextB} 
                onChange={(e) => setContextB(e.target.value)}
                className="flex-1 px-3 py-2 text-sm bg-background border border-border rounded-lg focus:ring-2 focus:ring-primary outline-none text-foreground"
                aria-required="true"
              />
            </div>
            <div className="flex justify-end pt-1">
              <m.button
                type="submit"
                disabled={!contextA.trim() || !contextB.trim() || isLoading}
                whileHover={{ scale: MotionScales.hover }}
                whileTap={{ scale: MotionScales.tap }}
                className="px-4 py-2 text-sm font-medium text-primary-foreground bg-primary hover:bg-primary/95 rounded-lg disabled:opacity-50 transition-colors"
              >
                Run Comparison
              </m.button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleSubmit} className="relative flex items-end">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isLoading ? 'AI is thinking...' : 'Ask a question...'}
              className="w-full py-3 pl-4 pr-24 text-sm text-foreground bg-muted/15 border border-border/60 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary focus:bg-background transition-colors placeholder:text-muted-foreground/50"
              rows={1}
              style={{ minHeight: '52px', maxHeight: '120px' }}
              disabled={isLoading || !conversationId}
            />
            <div className="absolute right-2 bottom-2 flex items-center gap-1">
              {!isLoading && (
                <m.button
                  type="button"
                  onClick={() => setShowComparePanel(true)}
                  whileHover={{ scale: MotionScales.hover }}
                  whileTap={{ scale: MotionScales.tap }}
                  className="p-2 text-muted-foreground hover:text-primary transition-colors hover:bg-muted rounded-lg"
                  title="Compare Topics"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" /></svg>
                </m.button>
              )}
              {isLoading ? (
                <m.button
                  type="button"
                  onClick={stopGeneration}
                  whileHover={{ scale: MotionScales.hover }}
                  whileTap={{ scale: MotionScales.tap }}
                  className="p-2 text-muted-foreground hover:text-foreground transition-colors bg-muted rounded-lg hover:bg-muted/80"
                  title="Stop generation"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10h6v4H9z" />
                  </svg>
                </m.button>
              ) : (
                <m.button
                  type="submit"
                  disabled={!input.trim() || !conversationId}
                  whileHover={{ scale: MotionScales.hover }}
                  whileTap={{ scale: MotionScales.tap }}
                  className="p-2 text-primary-foreground bg-primary rounded-lg hover:bg-primary/95 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <svg className="w-5 h-5 transform rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                </m.button>
              )}
            </div>
          </form>
        )}
        <div className="mt-2 text-center">
          <p className="text-[10px] text-muted-foreground/60">AI can make mistakes. Check the citations.</p>
        </div>
      </div>
    </div>
  );
};
