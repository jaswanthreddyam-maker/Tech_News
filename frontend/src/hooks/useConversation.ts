import { useState, useCallback, useRef, useEffect } from 'react';
import { apiFetch, apiClient } from '@/lib/api/client';
import { useAppStore } from '@/store/useStore';

export type ConversationMode = 'GENERAL' | 'ARTICLE' | 'COMPARISON' | 'ELI15' | 'TIMELINE' | 'DIGEST' | 'TOPIC' | 'WORKSPACE';
export type CapabilityError = 'OFFLINE' | 'UNAUTHORIZED' | 'STREAM_UNSUPPORTED' | 'RATE_LIMITED' | null;

export interface Citation {
  article_id: number;
  title: string;
  url?: string;
  score: number;
  confidence?: string;  // "High" | "Medium" | "Low"
}

export interface ComparisonContext {
  type: 'query' | 'article' | 'topic' | 'company' | 'product' | 'timespan';
  value: string;
}

export interface ComparisonMetadata {
  context_a: { name: string; sources: number };
  context_b: { name: string; sources: number };
}

export interface ProvenanceItem {
  type: 'article' | 'note' | 'comparison' | 'conversation';
  id: string | number;
  title?: string;
  url?: string;
}

export interface ProvenanceData {
  summary: {
    articles: number;
    notes: number;
    comparisons: number;
    conversations: number;
  };
  items: ProvenanceItem[];
  confidence?: string;
}

export interface EvidenceItem {
  id: string | number;
  type: 'article' | 'entity' | 'topic' | 'timeline_event' | 'relationship' | 'note' | 'comparison' | 'conversation';
  title?: string;
  url?: string;
  description?: string;
  score?: number;
}

export interface EvidenceBundle {
  items: EvidenceItem[];
  confidence?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  followUps?: string[];
  comparisonMetadata?: ComparisonMetadata;
  provenance?: ProvenanceData;
  evidence?: EvidenceBundle;
  status?: 'searching' | 'generating' | 'completed' | 'error';
}

interface UseConversationReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  mode: ConversationMode;
  title: string;
  setMode: (mode: ConversationMode) => void;
  sendMessage: (content: string, contextA?: ComparisonContext, contextB?: ComparisonContext) => Promise<void>;
  stopGeneration: () => void;
  capabilityError: CapabilityError;
  checkCapability: () => Promise<void>;
}

export function useConversation(
  conversationId: string | null,
  initialMode: ConversationMode = 'GENERAL',
  articleId?: number,
  workspaceId?: number
): UseConversationReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState<ConversationMode>(initialMode);
  const [title, setTitle] = useState('New Conversation');
  const [capabilityError, setCapabilityError] = useState<CapabilityError>(null);

  const { user } = useAppStore();

  const checkCapability = useCallback(async () => {
    if (typeof window !== 'undefined' && !navigator.onLine) {
      setCapabilityError('OFFLINE');
      return;
    }
    if (!user) {
      setCapabilityError('UNAUTHORIZED');
      return;
    }
    if (typeof window !== 'undefined' && !window.ReadableStream) {
      setCapabilityError('STREAM_UNSUPPORTED');
      return;
    }
    try {
      await apiFetch('/health/live');
      setCapabilityError(null);
    } catch (err: any) {
      if (err && err.status === 429) {
        setCapabilityError('RATE_LIMITED');
      } else {
        setCapabilityError('OFFLINE');
      }
    }
  }, [user]);

  useEffect(() => {
    checkCapability();
    if (typeof window !== 'undefined') {
      window.addEventListener('online', checkCapability);
      window.addEventListener('offline', checkCapability);
      return () => {
        window.removeEventListener('online', checkCapability);
        window.removeEventListener('offline', checkCapability);
      };
    }
  }, [checkCapability]);

  const abortControllerRef = useRef<AbortController | null>(null);
  const didLoadHistory = useRef(false);

  // Load existing conversation history if conversationId is provided
  useEffect(() => {
    if (!conversationId || didLoadHistory.current) return;
    didLoadHistory.current = true;

    (async () => {
      try {
        const data = await apiFetch<any>(`/chat/conversations/${conversationId}`);

        if (data.metadata?.title) {
          setTitle(data.metadata.title);
        }
        if (data.metadata?.mode) {
          setMode(data.metadata.mode as ConversationMode);
        }

        if (data.messages && data.messages.length > 0) {
          const loaded: ChatMessage[] = data.messages.map(
            (m: any, i: number) => ({
              id: `loaded-${i}`,
              role: m.role === 'user' ? 'user' : 'assistant',
              content: m.content,
              status: 'completed' as const,
            })
          );
          setMessages(loaded);
        }
      } catch (err) {
        // eslint-disable-next-line no-console

      }
    })();
  }, [conversationId]);

  // Reset when conversationId changes
  useEffect(() => {
    didLoadHistory.current = false;
    setMessages([]);
    setTitle('New Conversation');
  }, [conversationId]);

  const sendMessage = useCallback(
    async (content: string, contextA?: ComparisonContext, contextB?: ComparisonContext) => {
      await checkCapability();
      if (!content.trim() || !conversationId) return;

      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'user',
        content,
      };

      const assistantMessageId = (Date.now() + 1).toString();
      const initialAssistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        status: 'searching',
      };

      setMessages((prev) => [...prev, userMessage, initialAssistantMessage]);
      setIsLoading(true);

      abortControllerRef.current = new AbortController();

      try {
        const response = await apiClient.fetchRaw('/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            conversation_id: conversationId,
            message: content,
            mode,
            article_id: articleId,
            workspace_id: workspaceId,
            context_a: contextA,
            context_b: contextB,
          }),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok || !response.body) {
          throw new Error('Network response was not ok');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.substring(6);
              try {
                const eventData = JSON.parse(dataStr);

                setMessages((prev) => {
                  const newMessages = [...prev];
                  const msgIndex = newMessages.findIndex(
                    (m) => m.id === assistantMessageId
                  );
                  if (msgIndex === -1) return prev;

                  const msg = { ...newMessages[msgIndex] };

                  switch (eventData.event) {
                    case 'retrieval_started':
                      msg.status = 'searching';
                      break;
                    case 'retrieval_finished':
                      break;
                    case 'provenance':
                      msg.provenance = eventData.data;
                      break;
                    case 'evidence_bundle':
                      msg.evidence = eventData.data;
                      break;
                    case 'comparison_metadata':
                      msg.comparisonMetadata = eventData.data;
                      break;
                    case 'generation_started':
                      msg.status = 'generating';
                      break;
                    case 'token':
                      msg.content += eventData.data.text;
                      break;
                    case 'citation':
                      msg.citations = eventData.data.citations;
                      break;
                    case 'suggested_follow_ups':
                      msg.followUps = eventData.data.follow_ups;
                      break;
                    case 'title_generated':
                      setTitle(eventData.data.title);
                      break;
                    case 'completed':
                      msg.status = 'completed';
                      setIsLoading(false);
                      break;
                    case 'error':
                      msg.status = 'error';
                      msg.content += `\n\n**Error:** ${eventData.data.message}`;
                      setIsLoading(false);
                      break;
                  }

                  newMessages[msgIndex] = msg;
                  return newMessages;
                });
              } catch (err) {
                // eslint-disable-next-line no-console

              }
            }
          }
        }
      } catch (error: any) {
        if (error.name !== 'AbortError') {
          // eslint-disable-next-line no-console

          setMessages((prev) => {
            const newMessages = [...prev];
            const msgIndex = newMessages.findIndex(
              (m) => m.id === assistantMessageId
            );
            if (msgIndex !== -1) {
              newMessages[msgIndex] = {
                ...newMessages[msgIndex],
                status: 'error',
                content:
                  newMessages[msgIndex].content +
                  '\n\n**Network Error:** Could not connect to AI service.',
              };
            }
            return newMessages;
          });
        }
      } finally {
        setIsLoading(false);
      }
    },
    [conversationId, mode, articleId, workspaceId, checkCapability]
  );

  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsLoading(false);
    }
  }, []);

  return {
    messages,
    isLoading,
    mode,
    title,
    setMode,
    sendMessage,
    stopGeneration,
    capabilityError,
    checkCapability,
  };
}
