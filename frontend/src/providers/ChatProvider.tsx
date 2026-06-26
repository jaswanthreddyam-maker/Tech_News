'use client';

import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export type ConversationMode = 'GENERAL' | 'ARTICLE' | 'COMPARISON' | 'ELI15' | 'TIMELINE' | 'DIGEST' | 'TOPIC';

export interface ConversationMeta {
  conversation_id: string;
  title: string;
  mode: ConversationMode;
  article_id?: number | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

interface ChatContextValue {
  /** The active conversation ID, or null if none selected. */
  activeConversationId: string | null;

  /** List of conversations owned by this user. */
  conversations: ConversationMeta[];

  /** Creates a new conversation via POST /conversations and selects it. */
  createConversation: (mode?: ConversationMode, articleId?: number) => Promise<string>;

  /** Selects an existing conversation (e.g., from sidebar). */
  selectConversation: (conversationId: string) => void;

  /** Renames a conversation. */
  renameConversation: (conversationId: string, title: string) => Promise<void>;

  /** Deletes a conversation. */
  deleteConversation: (conversationId: string) => Promise<void>;

  /** Refreshes the conversation list from the API. */
  refreshConversations: () => Promise<void>;

  /** Whether we are loading the conversation list. */
  isLoadingList: boolean;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export function useChatContext() {
  const ctx = useContext(ChatContext);
  if (!ctx) {
    throw new Error('useChatContext must be used within a ChatProvider');
  }
  return ctx;
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------
export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationMeta[]>([]);
  const [isLoadingList, setIsLoadingList] = useState(false);
  const didFetch = useRef(false);

  // Fetch conversation list on mount
  const refreshConversations = useCallback(async () => {
    setIsLoadingList(true);
    try {
      const res = await fetch('/api/v1/chat/conversations');
      if (res.ok) {
        const data = await res.json();
        setConversations(data.conversations || []);
      }
    } catch (err) {
      // eslint-disable-next-line no-console

    } finally {
      setIsLoadingList(false);
    }
  }, []);

  useEffect(() => {
    if (!didFetch.current) {
      didFetch.current = true;
      refreshConversations();
    }
  }, [refreshConversations]);

  const createConversation = useCallback(
    async (mode: ConversationMode = 'GENERAL', articleId?: number): Promise<string> => {
      try {
        const res = await fetch('/api/v1/chat/conversations', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mode, article_id: articleId }),
        });
        if (!res.ok) throw new Error('Failed to create conversation');
        const data = await res.json();
        const newId = data.conversation_id as string;

        // Optimistically prepend to list
        setConversations((prev) => [data.metadata as ConversationMeta, ...prev]);
        setActiveConversationId(newId);
        return newId;
      } catch (err) {
        // eslint-disable-next-line no-console

        throw err;
      }
    },
    []
  );

  const selectConversation = useCallback((conversationId: string) => {
    setActiveConversationId(conversationId);
  }, []);

  const renameConversation = useCallback(
    async (conversationId: string, title: string) => {
      try {
        await fetch(`/api/v1/chat/conversations/${conversationId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title }),
        });
        setConversations((prev) =>
          prev.map((c) =>
            c.conversation_id === conversationId ? { ...c, title } : c
          )
        );
      } catch (err) {
        // eslint-disable-next-line no-console

      }
    },
    []
  );

  const deleteConversation = useCallback(
    async (conversationId: string) => {
      try {
        await fetch(`/api/v1/chat/conversations/${conversationId}`, {
          method: 'DELETE',
        });
        setConversations((prev) =>
          prev.filter((c) => c.conversation_id !== conversationId)
        );
        if (activeConversationId === conversationId) {
          setActiveConversationId(null);
        }
      } catch (err) {
        // eslint-disable-next-line no-console

      }
    },
    [activeConversationId]
  );

  const value: ChatContextValue = {
    activeConversationId,
    conversations,
    createConversation,
    selectConversation,
    renameConversation,
    deleteConversation,
    refreshConversations,
    isLoadingList,
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}
