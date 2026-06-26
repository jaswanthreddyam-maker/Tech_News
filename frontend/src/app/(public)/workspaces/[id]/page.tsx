/* eslint-disable react/jsx-no-comment-textnodes, react/no-unescaped-entities */
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api/client";
import Link from "next/link";
import { ConversationalSearch } from "@/components/ai/ConversationalSearch";
import { NotebookEditor } from "@/components/workspace/NotebookEditor";
import { Skeleton } from "@/design-system/components/Skeleton";
import { useLoadingState } from "@/design-system/hooks/useLoadingState";
import { Pin, FileText, Clock, Bot, Search } from "lucide-react";
import { EmptyState, EmptyIllustration } from "@/components/common/EmptyState";

import { notFound } from "next/navigation";

export default function WorkspaceDashboard() {
  if (true as boolean) {
    notFound();
  }
  const params = useParams();
  const workspaceId = parseInt(params.id as string, 10);

  const [workspace, setWorkspace] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'articles' | 'notes' | 'timeline' | 'digest' | 'chat'>('articles');
  const [timeline, setTimeline] = useState<any[]>([]);
  const [digests, setDigests] = useState<any[]>([]);
  const [activeDigestId, setActiveDigestId] = useState<number | null>(null);
  const [generatingDigest, setGeneratingDigest] = useState(false);
  const [streamingDigestContent, setStreamingDigestContent] = useState("");

  const [newNote, setNewNote] = useState("");
  const [activeNoteId, setActiveNoteId] = useState<number | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[] | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    fetchWorkspace();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId]);

  useEffect(() => {
    if (activeTab === 'timeline') {
      fetchTimeline();
    } else if (activeTab === 'digest') {
      fetchDigests();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, workspaceId]);

  const fetchDigests = async () => {
    try {
      const data: any = await apiFetch(`/workspaces/${workspaceId}/digests`);
      setDigests(data);
      if (data.length > 0 && !activeDigestId) {
        setActiveDigestId(data[0].id);
      }
    } catch (err: any) {
      if (err?.status !== 404 && err?.name !== "NotFoundError") {
        // eslint-disable-next-line no-console

      }
    }
  };

  const fetchTimeline = async () => {
    try {
      const data = await apiFetch(`/workspaces/${workspaceId}/timeline`);
      setTimeline(data as any[]);
    } catch (err: any) {
      if (err?.status !== 404 && err?.name !== "NotFoundError") {
        // eslint-disable-next-line no-console

      }
    }
  };

  const fetchWorkspace = async () => {
    try {
      const data = await apiFetch(`/workspaces/${workspaceId}`);
      setWorkspace(data);
    } catch (err: any) {
      if (err?.status !== 404 && err?.name !== "NotFoundError") {
        // eslint-disable-next-line no-console

      }
    } finally {
      setLoading(false);
    }
  };

  const handleAddNote = async () => {
    if (!newNote.trim()) return;
    try {
      await apiFetch(`/workspaces/${workspaceId}/notes`, {
        method: "POST",
        body: JSON.stringify({ content: newNote }),
      });
      setNewNote("");
      fetchWorkspace(); // Refresh
    } catch (err) {
      // eslint-disable-next-line no-console

    }
  };

  const handleUpdateNote = async (noteId: number, content: string, title: string) => {
    try {
      await apiFetch(`/workspaces/${workspaceId}/notes/${noteId}`, {
        method: "PUT",
        body: JSON.stringify({ content, title }),
      });
      fetchWorkspace(); // Refresh list to get updated titles/summaries
    } catch (err) {
      // eslint-disable-next-line no-console

    }
  };

  const handleSummarizeNote = async (noteId: number) => {
    try {
      await apiFetch(`/workspaces/${workspaceId}/notes/${noteId}/summarize`, {
        method: "POST"
      });
      fetchWorkspace();
    } catch (err) {
      // eslint-disable-next-line no-console

    }
  };

  const handleSearchNotes = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }
    setIsSearching(true);
    try {
      const data = await apiFetch(`/workspaces/${workspaceId}/notes/search/query?q=${encodeURIComponent(searchQuery)}`);
      setSearchResults(data as any[]);
    } catch (err) {
      // eslint-disable-next-line no-console

    } finally {
      setIsSearching(false);
    }
  };

  const handleDeleteArticle = async (articleId: number) => {
    try {
      await apiFetch(`/workspaces/${workspaceId}/articles/${articleId}`, {
        method: "DELETE",
      });
      fetchWorkspace(); // Refresh
    } catch (err) {
      // eslint-disable-next-line no-console

    }
  };

  const handleDeleteNote = async (noteId: number) => {
    try {
      await apiFetch(`/workspaces/${workspaceId}/notes/${noteId}`, {
        method: "DELETE",
      });
      fetchWorkspace(); // Refresh
    } catch (err) {
      // eslint-disable-next-line no-console

    }
  };

  const generateNewDigest = async () => {
    setGeneratingDigest(true);
    setStreamingDigestContent("");
    setActiveDigestId(null); // Deselect so we show the streaming view

    try {
      const response = await fetch(`/api/v1/workspaces/${workspaceId}/digests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      
      if (!reader) return;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n\n');
        
        for (const line of lines) {
          if (line.startsWith('event: token')) {
            const dataStr = line.replace('event: token\ndata: ', '');
            try {
              const data = JSON.parse(dataStr);
              setStreamingDigestContent(prev => prev + data.text);
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            } catch(e) {}
          } else if (line.startsWith('event: completed')) {
            fetchDigests();
            setGeneratingDigest(false);
          }
        }
      }
    } catch (e) {
      // eslint-disable-next-line no-console

      setGeneratingDigest(false);
    }
  };

  const loadingLevel = useLoadingState(loading);

  if (loading) {
    return (
      <div className="flex h-[calc(100vh-64px)] bg-gray-50">
        <div className="flex-1 flex flex-col min-w-[300px] border-r border-gray-200 bg-white overflow-hidden">
          <div className="p-6 border-b border-gray-100 flex flex-col gap-2">
            <Skeleton level={loadingLevel} className="h-4 w-32 mb-2" />
            <Skeleton level={loadingLevel} className="h-8 w-64" />
            <Skeleton level={loadingLevel} className="h-4 w-48 mt-1" />
          </div>
          <div className="flex border-b border-gray-200 px-6 pt-4 space-x-6">
            {[1, 2, 3, 4].map(i => (
              <Skeleton key={i} level={loadingLevel} className="h-5 w-24 mb-3" />
            ))}
          </div>
          <div className="flex-1 overflow-y-auto p-6 bg-gray-50 space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm flex items-start justify-between">
                <div className="flex-1 space-y-2">
                  <Skeleton level={loadingLevel} className="h-5 w-3/4" />
                  <Skeleton level={loadingLevel} className="h-4 w-full" />
                  <Skeleton level={loadingLevel} className="h-4 w-5/6" />
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="hidden md:flex md:w-[450px] lg:w-[500px] flex-col bg-white border-l border-gray-200 shadow-[-4px_0_15px_-3px_rgba(0,0,0,0.05)] z-10">
          <div className="p-4 border-b border-gray-100 bg-gray-50/50 flex items-center justify-between">
            <Skeleton level={loadingLevel} className="h-5 w-40" />
            <Skeleton level={loadingLevel} className="h-6 w-24 rounded" />
          </div>
          <div className="flex-1 p-4 flex flex-col gap-4">
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <Skeleton level={loadingLevel} className="w-12 h-12 rounded-full" />
              <Skeleton level={loadingLevel} className="h-4 w-64" />
              <div className="flex gap-2">
                <Skeleton level={loadingLevel} className="h-8 w-24 rounded-full" />
                <Skeleton level={loadingLevel} className="h-8 w-24 rounded-full" />
              </div>
            </div>
            <div className="mt-auto">
              <Skeleton level={loadingLevel} className="h-12 w-full rounded-xl" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!workspace) {
    return <div className="p-8 max-w-7xl mx-auto text-red-500">Workspace not found.</div>;
  }

  return (
    <div className="flex h-[calc(100vh-64px)] bg-gray-50">
      {/* Left Pane: Content Management */}
      <div className="flex-1 flex flex-col min-w-[300px] border-r border-gray-200 bg-white overflow-hidden">
        
        {/* Header */}
        <div className="p-6 border-b border-gray-100 flex items-center justify-between">
          <div>
            <Link href="/workspaces" className="text-sm text-gray-500 hover:text-primary-600 flex items-center mb-2 font-mono">
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18"/></svg>
              Back to Workspaces
            </Link>
            <h1 className="text-2xl font-bold font-mono">{workspace.name}</h1>
            <p className="text-sm text-gray-500 mt-1">{workspace.description || "Research Workspace"}</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 px-6 pt-4 space-x-6">
          <button 
            onClick={() => setActiveTab('articles')}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'articles' ? 'border-primary-600 text-primary-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            Pinned Articles ({workspace.articles?.length || 0})
          </button>
          <button 
            onClick={() => setActiveTab('notes')}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'notes' ? 'border-primary-600 text-primary-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            My Notes ({workspace.notes?.length || 0})
          </button>
          <button 
            onClick={() => setActiveTab('timeline')}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'timeline' ? 'border-primary-600 text-primary-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            Timeline
          </button>
          <button 
            onClick={() => setActiveTab('digest')}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'digest' ? 'border-primary-600 text-primary-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            Daily Digest
          </button>
          <button 
            onClick={() => setActiveTab('chat')}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors md:hidden ${activeTab === 'chat' ? 'border-primary-600 text-primary-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            AI Assistant
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
          
          {/* ARTICLES TAB */}
          {activeTab === 'articles' && (
            <div className="space-y-4">
              {workspace.articles?.length === 0 ? (
                <EmptyState>
                  <EmptyIllustration
                    icon={Pin}
                    title="No articles pinned yet"
                    description="Browse articles and click 'Pin to Workspace' to save them here."
                  />
                </EmptyState>
              ) : (
                workspace.articles?.map((wa: any) => (
                  <div key={wa.id} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm flex items-start justify-between group">
                    <div className="flex-1 min-w-0 pr-4">
                      <h3 className="font-semibold text-gray-900 truncate">
                        <Link href={`/articles/${wa.article.slug}`} className="hover:text-primary-600 transition-colors">
                          {wa.article.title}
                        </Link>
                      </h3>
                      <p className="text-xs text-gray-500 mt-1 line-clamp-2">{wa.article.summary}</p>
                    </div>
                    <button 
                      onClick={() => handleDeleteArticle(wa.article_id)}
                      className="text-gray-400 hover:text-red-500 p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                      title="Remove from Workspace"
                    >
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                    </button>
                  </div>
                ))
              )}
            </div>
          )}

          {/* NOTES TAB */}
          {activeTab === 'notes' && (
            <div className="h-full flex flex-col">
              {activeNoteId ? (
                <div className="flex-1 flex flex-col h-full space-y-4">
                  <div className="flex justify-between items-center">
                    <button 
                      onClick={() => setActiveNoteId(null)}
                      className="text-sm font-medium text-gray-500 hover:text-gray-800 flex items-center"
                    >
                      <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
                      Back to Notes
                    </button>
                  </div>
                  {(() => {
                    const activeNote = workspace.notes.find((n: any) => n.id === activeNoteId);
                    if (!activeNote) return null;
                    return (
                      <NotebookEditor 
                        workspaceId={workspaceId}
                        noteId={activeNote.id}
                        initialContent={activeNote.content}
                        initialTitle={activeNote.title || "Untitled Note"}
                        onSave={handleUpdateNote}
                        onSummarize={handleSummarizeNote}
                        className="flex-1"
                      />
                    );
                  })()}
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Add Note */}
                  <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm flex gap-3 items-center">
                    <input
                      type="text"
                      value={newNote}
                      onChange={(e) => setNewNote(e.target.value)}
                      placeholder="Start a new research note..."
                      className="flex-1 border border-gray-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary-500"
                      onKeyDown={(e) => { if(e.key === 'Enter') handleAddNote() }}
                    />
                    <button 
                      onClick={handleAddNote}
                      disabled={!newNote.trim()}
                      className="px-4 py-2 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700 transition-colors disabled:opacity-50"
                    >
                      Create Note
                    </button>
                  </div>

                  {/* Note List */}
                  <div className="space-y-4">
                    <div className="mb-6 flex flex-col gap-2">
                      <form onSubmit={handleSearchNotes} className="flex gap-2">
                        <div className="relative flex-1">
                          <input 
                            type="text"
                            value={searchQuery}
                            onChange={(e) => {
                              setSearchQuery(e.target.value);
                              if (!e.target.value) setSearchResults(null);
                            }}
                            placeholder="Semantic search your notes..."
                            className="w-full border border-gray-200 rounded-md pl-9 pr-3 py-2 text-sm focus:outline-none focus:border-primary-500"
                          />
                          <svg className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                        </div>
                        <button type="submit" disabled={isSearching || !searchQuery.trim()} className="px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md text-sm font-medium transition-colors disabled:opacity-50">
                          {isSearching ? 'Searching...' : 'Search'}
                        </button>
                      </form>
                      {searchResults && (
                        <div className="flex justify-between items-center text-xs text-gray-500">
                          <span>Found {searchResults.length} results</span>
                          <button onClick={() => {setSearchQuery(''); setSearchResults(null)}} className="hover:text-primary-600">Clear Search</button>
                        </div>
                      )}
                    </div>

                    {(searchResults || workspace.notes)?.length === 0 ? (
                      <EmptyState size="sm">
                        <EmptyIllustration
                          icon={searchResults ? Search : FileText}
                          title={searchResults ? "No results found" : "No notes added yet"}
                          description={searchResults ? "Try a different search query." : "Start typing above to create your first note."}
                        />
                      </EmptyState>
                    ) : (
                      <div className="grid grid-cols-1 gap-4">
                        {(searchResults || workspace.notes)?.map((note: any) => (
                          <div 
                            key={note.id} 
                            className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm group relative flex flex-col hover:border-primary-300 transition-colors cursor-pointer" 
                            onClick={() => setActiveNoteId(note.id)}
                            role="button"
                            tabIndex={0}
                            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setActiveNoteId(note.id); } }}
                          >
                            <div className="flex justify-between items-start mb-2">
                              <h3 className="font-semibold text-gray-900 truncate pr-8">
                                {note.title || "Untitled Note"}
                                {note.score !== undefined && (
                                  <span className="ml-2 text-[10px] bg-primary-100 text-primary-800 px-1.5 py-0.5 rounded-full inline-flex align-middle">
                                    {(note.score * 100).toFixed(0)}% match
                                  </span>
                                )}
                              </h3>
                            </div>
                            {note.excerpt ? (
                              // eslint-disable-next-line react/no-unescaped-entities
                              <p className="text-sm text-gray-700 mb-3 flex-1 italic bg-yellow-50 p-2 rounded">"...{note.excerpt}..."</p>
                            ) : (
                              <p className="text-sm text-gray-500 line-clamp-2 mb-3 flex-1">{note.summary || note.content}</p>
                            )}
                            
                            <div className="flex items-center justify-between mt-auto pt-3 border-t border-gray-50">
                              <div className="text-xs text-gray-400 font-mono flex items-center gap-2">
                                <span>v{note.version_number}</span>
                                {note.updated_at && (
                                  <>
                                    <span>&bull;</span>
                                    <span>{new Date(note.updated_at).toLocaleDateString()}</span>
                                  </>
                                )}
                              </div>
                              <div className="flex items-center gap-2">
                                <button 
                                  onClick={(e) => { e.stopPropagation(); handleSummarizeNote(note.id); }}
                                  className="text-xs text-primary-600 hover:text-primary-800 hover:bg-primary-50 px-2 py-1 rounded transition-colors"
                                >
                                  ✨ Auto-Summary
                                </button>
                                <button 
                                  onClick={(e) => { e.stopPropagation(); handleDeleteNote(note.id); }}
                                  className="text-gray-400 hover:text-red-500 p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                                  title="Delete Note"
                                >
                                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                                </button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TIMELINE TAB */}
          {activeTab === 'timeline' && (
            <div className="space-y-6">
              {timeline.length === 0 ? (
                <EmptyState>
                  <EmptyIllustration
                    icon={Clock}
                    title="No activity recorded"
                    description="Events like pinning articles and adding notes will appear here."
                  />
                </EmptyState>
              ) : (
                <div className="relative border-l border-gray-200 ml-3 pl-4 space-y-6">
                  {timeline.map((event) => {
                    const date = new Date(event.created_at);
                    
                    let label = "Activity";
                    switch(event.event_type) {
                      case 'ARTICLE_PINNED': label = `Pinned Article: ${event.metadata?.article_id || ''}`; break;
                      case 'ARTICLE_UNPINNED': label = `Unpinned Article: ${event.metadata?.article_id || ''}`; break;
                      case 'NOTE_CREATED': label = `Added Note`; break;
                      case 'NOTE_UPDATED': label = `Updated Note`; break;
                      case 'NOTE_DELETED': label = `Deleted Note`; break;
                      case 'CHAT_STARTED': label = `Started Conversation`; break;
                      case 'WORKSPACE_CREATED': label = `Created Workspace`; break;
                      case 'WORKSPACE_RENAMED': label = `Renamed to ${event.metadata?.new_name || ''}`; break;
                    }

                    return (
                      <div key={event.id} className="relative">
                        <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 bg-primary-400 rounded-full border border-white"></div>
                        <div className="flex flex-col">
                          <span className="text-xs text-gray-400 font-mono mb-0.5">
                            {date.toLocaleDateString()} at {date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                          </span>
                          <span className="text-sm text-gray-800">{label}</span>
                          {event.metadata?.content_preview && (
                            <span className="text-xs text-gray-500 italic mt-1 line-clamp-1 border-l-2 border-gray-200 pl-2">
                              // eslint-disable-next-line react/no-unescaped-entities
                              "{event.metadata.content_preview}..."
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* DIGEST TAB */}
          {activeTab === 'digest' && (
            <div className="h-full flex gap-6">
              {/* Digest Sidebar */}
              <div className="w-1/3 border-r border-gray-200 pr-4 flex flex-col">
                <button 
                  onClick={generateNewDigest}
                  disabled={generatingDigest}
                  className="w-full mb-6 px-4 py-2 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700 transition-colors disabled:opacity-50"
                >
                  {generatingDigest ? "Generating..." : "Generate New Digest"}
                </button>
                <div className="flex-1 overflow-y-auto space-y-2">
                  {digests.map((d: any) => (
                    <button
                      key={d.id}
                      onClick={() => setActiveDigestId(d.id)}
                      className={`w-full text-left p-3 rounded-lg border text-sm transition-colors ${
                        activeDigestId === d.id ? 'bg-primary-50 border-primary-200 text-primary-900' : 'bg-white border-gray-200 text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      <div className="font-semibold">{new Date(d.created_at).toLocaleDateString()}</div>
                      <div className="text-xs text-gray-500 mt-1">Since {new Date(d.since_time).toLocaleDateString()}</div>
                    </button>
                  ))}
                  {digests.length === 0 && !generatingDigest && (
                    <p className="text-sm text-gray-500 text-center py-4">No digests generated yet.</p>
                  )}
                </div>
              </div>

              {/* Digest Content */}
              <div className="flex-1 overflow-y-auto pl-2">
                {generatingDigest ? (
                  <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
                    <div className="flex items-center gap-2 mb-4">
                      <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse"></div>
                      <span className="text-sm font-mono text-gray-500 uppercase tracking-wider">Generating Digest...</span>
                    </div>
                    <div className="prose prose-sm max-w-none font-sans text-gray-800 whitespace-pre-wrap">
                      {streamingDigestContent}
                    </div>
                  </div>
                ) : activeDigestId ? (
                  <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm relative group">
                    <button 
                      onClick={async () => {
                        const digest = digests.find(d => d.id === activeDigestId);
                        if (digest) {
                          await apiFetch(`/workspaces/${workspaceId}/notes`, {
                            method: 'POST',
                            body: JSON.stringify({
                              title: `Digest: ${new Date(digest.created_at).toLocaleDateString()}`,
                              content: `![[Digest:${new Date(digest.created_at).toLocaleDateString()}]]\n\n${digest.content}`
                            })
                          });
                          fetchWorkspace();
                          setActiveTab('notes');
                        }
                      }}
                      className="absolute top-4 right-4 text-xs font-medium bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      Save as Note
                    </button>
                    {(() => {
                      const digest = digests.find(d => d.id === activeDigestId);
                      if (!digest) return null;
                      return (
                        <>
                          <div className="mb-6 pb-4 border-b border-gray-100">
                            <h2 className="text-xl font-bold mb-2">Daily Digest</h2>
                            <div className="text-sm text-gray-500 flex gap-4">
                              <span>Generated: {new Date(digest.created_at).toLocaleString()}</span>
                              <span>•</span>
                              <span>Since: {new Date(digest.since_time).toLocaleString()}</span>
                            </div>
                          </div>
                          
                          {/* Rich rendering of the markdown content would ideally go through ReactMarkdown,
                              but for now we just render it with pre-wrap for structure */}
                          <div className="prose prose-sm max-w-none font-sans text-gray-800 whitespace-pre-wrap">
                            {digest.content}
                          </div>
                        </>
                      );
                    })()}
                  </div>
                ) : (
                  <EmptyState>
                    <EmptyIllustration
                      icon={Bot}
                      title="No digest selected"
                      description="Select a digest from the sidebar or generate a new one."
                    />
                  </EmptyState>
                )}
              </div>
            </div>
          )}
          
          {/* Mobile Chat Tab (hidden on desktop) */}
          <div className={`md:hidden ${activeTab === 'chat' ? 'block' : 'hidden'} h-full`}>
             <div className="h-[600px] border border-gray-200 rounded-xl overflow-hidden bg-white">
              <ConversationalSearch 
                conversationId={null}
                initialMode="WORKSPACE" 
                workspaceId={workspaceId} 
              />
            </div>
          </div>

        </div>
      </div>

      {/* Right Pane: AI Assistant (Hidden on mobile when not active tab) */}
      <div className={`hidden md:flex md:w-[450px] lg:w-[500px] flex-col bg-white border-l border-gray-200 shadow-[-4px_0_15px_-3px_rgba(0,0,0,0.05)] z-10`}>
        <div className="p-4 border-b border-gray-100 bg-gray-50/50 flex items-center justify-between">
          <div className="flex items-center">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
            <h2 className="font-semibold text-sm font-mono text-gray-700">Workspace Assistant</h2>
          </div>
          <div className="text-xs bg-primary-100 text-primary-700 px-2 py-1 rounded font-medium">
            WORKSPACE MODE
          </div>
        </div>
        
        <div className="flex-1 overflow-hidden">
          <ConversationalSearch 
            conversationId={null}
            initialMode="WORKSPACE" 
            workspaceId={workspaceId} 
          />
        </div>
      </div>

    </div>
  );
}
