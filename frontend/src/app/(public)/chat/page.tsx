/* eslint-disable react/jsx-no-comment-textnodes, react/no-unescaped-entities */
'use client';

// eslint-disable-next-line @typescript-eslint/no-unused-vars
import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { ChatProvider, useChatContext, ConversationMeta } from '@/providers/ChatProvider';
import { ConversationalSearch } from '@/components/ai/ConversationalSearch';

// ---------------------------------------------------------------------------
// Date grouping helper
// ---------------------------------------------------------------------------
function groupByDate(conversations: ConversationMeta[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const lastWeek = new Date(today.getTime() - 7 * 86400000);

  const groups: { label: string; items: ConversationMeta[] }[] = [
    { label: 'Today', items: [] },
    { label: 'Yesterday', items: [] },
    { label: 'Last 7 Days', items: [] },
    { label: 'Older', items: [] },
  ];

  for (const conv of conversations) {
    const d = new Date(conv.updated_at || conv.created_at);
    if (d >= today) groups[0].items.push(conv);
    else if (d >= yesterday) groups[1].items.push(conv);
    else if (d >= lastWeek) groups[2].items.push(conv);
    else groups[3].items.push(conv);
  }

  return groups.filter((g) => g.items.length > 0);
}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------
function ChatSidebar() {
  const {
    activeConversationId,
    conversations,
    createConversation,
    selectConversation,
    renameConversation,
    deleteConversation,
    isLoadingList,
  } = useChatContext();

  const router = useRouter();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const handleNew = async () => {
    const id = await createConversation('GENERAL');
    router.push(`/chat?id=${id}`, { scroll: false });
  };

  const handleSelect = (id: string) => {
    selectConversation(id);
    router.push(`/chat?id=${id}`, { scroll: false });
  };

  const handleRename = async (id: string) => {
    if (editTitle.trim()) {
      await renameConversation(id, editTitle.trim());
    }
    setEditingId(null);
  };

  const handleDelete = async (id: string) => {
    await deleteConversation(id);
    if (activeConversationId === id) {
      router.push('/chat', { scroll: false });
    }
  };

  const grouped = groupByDate(conversations);

  return (
    <aside className="w-72 border-r border-gray-200 bg-gray-50/80 flex flex-col h-full">
      {/* New Chat Button */}
      <div className="p-3">
        <button
          onClick={handleNew}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Chat
        </button>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {isLoadingList ? (
          <div className="space-y-2 p-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-10 bg-gray-200 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-gray-400">
            No conversations yet.
            <br />
            // eslint-disable-next-line react/no-unescaped-entities
            Start by clicking "New Chat".
          </div>
        ) : (
          grouped.map((group) => (
            <div key={group.label} className="mb-4">
              <p className="px-3 py-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                {group.label}
              </p>
              {group.items.map((conv) => (
                <div
                  key={conv.conversation_id}
                  className={`group relative flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors ${
                    activeConversationId === conv.conversation_id
                      ? 'bg-primary-50 text-primary-700 font-medium'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                  onClick={() => handleSelect(conv.conversation_id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleSelect(conv.conversation_id); }}
                >
                  {editingId === conv.conversation_id ? (
                    <input
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onBlur={() => handleRename(conv.conversation_id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleRename(conv.conversation_id);
                        if (e.key === 'Escape') setEditingId(null);
                      }}
                      className="flex-1 text-sm bg-white border border-primary-300 rounded px-1.5 py-0.5 focus:outline-none"
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    <span className="flex-1 truncate">{conv.title}</span>
                  )}

                  {/* Actions (visible on hover) */}
                  <div className="hidden group-hover:flex items-center gap-1 shrink-0">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingId(conv.conversation_id);
                        setEditTitle(conv.title);
                      }}
                      className="p-1 rounded hover:bg-gray-200 text-gray-400 hover:text-gray-600"
                      title="Rename"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                        />
                      </svg>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(conv.conversation_id);
                      }}
                      className="p-1 rounded hover:bg-red-50 text-gray-400 hover:text-red-500"
                      title="Delete"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ))
        )}
      </div>
    </aside>
  );
}

// ---------------------------------------------------------------------------
// Main Chat Page Content
// ---------------------------------------------------------------------------
function ChatPageContent() {
  const { activeConversationId, createConversation, selectConversation } = useChatContext();
  const searchParams = useSearchParams();
  const router = useRouter();

  // Sync URL param with active conversation
  useEffect(() => {
    const idFromUrl = searchParams.get('id');
    if (idFromUrl && idFromUrl !== activeConversationId) {
      selectConversation(idFromUrl);
    }
  }, [searchParams, activeConversationId, selectConversation]);

  const handleNewChat = async () => {
    const id = await createConversation('GENERAL');
    router.push(`/chat?id=${id}`, { scroll: false });
  };

  return (
    <div className="flex h-[calc(100vh-64px)]">
      {/* Sidebar */}
      <ChatSidebar />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {activeConversationId ? (
          <ConversationalSearch
            conversationId={activeConversationId}
            initialMode="GENERAL"
            hideModeSelector={false}
            className="flex-1 border-0 rounded-none shadow-none max-h-full"
          />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
            <div className="max-w-md space-y-6">
              <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
                <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                  />
                </svg>
              </div>
              <h2 className="text-2xl font-semibold text-gray-800">Tech News AI</h2>
              <p className="text-gray-500 text-sm leading-relaxed">
                Ask questions about tech news, compare topics, explore timelines, or get simple
                explanations. All answers are grounded in our article database.
              </p>
              <button
                onClick={handleNewChat}
                className="inline-flex items-center gap-2 px-6 py-3 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Start a Conversation
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page (wrapped in ChatProvider)
// ---------------------------------------------------------------------------
export default function ChatPage() {
  return (
    <ChatProvider>
      <ChatPageContent />
    </ChatProvider>
  );
}
