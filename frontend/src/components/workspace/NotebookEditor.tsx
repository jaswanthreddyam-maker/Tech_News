import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import Link from 'next/link';

interface NoteVersion {
  id: number;
  version_number: number;
  change_type: string;
  created_by: string;
  created_at: string;
  content: string;
  summary: string;
}

interface NotebookEditorProps {
  workspaceId: number;
  noteId: number;
  initialContent: string;
  initialTitle: string;
  onSave: (id: number, content: string, title: string) => Promise<void>;
  onSummarize: (id: number) => Promise<void>;
  className?: string;
}

export const NotebookEditor: React.FC<NotebookEditorProps> = ({
  workspaceId,
  noteId,
  initialContent,
  initialTitle,
  onSave,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  onSummarize,
  className = ''
}) => {
  const [content, setContent] = useState(initialContent);
  const [title, setTitle] = useState(initialTitle);
  const [activeTab, setActiveTab] = useState<'edit' | 'preview'>('edit');
  const [isGenerating, setIsGenerating] = useState(false);
  
  // History panel
  const [showHistory, setShowHistory] = useState(false);
  const [versions, setVersions] = useState<NoteVersion[]>([]);
  
  // Selection bounds
  const [selection, setSelection] = useState({ start: 0, end: 0, text: '' });
  const [showAiMenu, setShowAiMenu] = useState(false);
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Discovery features
  const [backlinks, setBacklinks] = useState<any[]>([]);
  const [similarNotes, setSimilarNotes] = useState<any[]>([]);

  useEffect(() => {
    // Load discovery data
    const loadDiscovery = async () => {
      try {
        const [blRes, simRes] = await Promise.all([
          fetch(`/api/v1/workspaces/${workspaceId}/notes/${noteId}/backlinks`),
          fetch(`/api/v1/workspaces/${workspaceId}/notes/${noteId}/similar`)
        ]);
        if (blRes.ok) setBacklinks(await blRes.json());
        if (simRes.ok) setSimilarNotes(await simRes.json());
      } catch(e) {
        // eslint-disable-next-line no-console

      }
    };
    loadDiscovery();
  }, [workspaceId, noteId]);

  useEffect(() => {
    setContent(initialContent);
    setTitle(initialTitle);
  }, [initialContent, initialTitle]);

  const handleSelect = (e: React.SyntheticEvent<HTMLTextAreaElement>) => {
    const target = e.target as HTMLTextAreaElement;
    const start = target.selectionStart;
    const end = target.selectionEnd;
    const text = target.value.substring(start, end);
    setSelection({ start, end, text });
  };

  const handleContextMenu = (e: React.MouseEvent<HTMLTextAreaElement>) => {
    if (selection.text) {
      e.preventDefault();
      setShowAiMenu(true);
      setMenuPosition({ top: e.clientY, left: e.clientX });
    }
  };

  useEffect(() => {
    const handleClickOutside = () => setShowAiMenu(false);
    window.addEventListener('click', handleClickOutside);
    return () => window.removeEventListener('click', handleClickOutside);
  }, []);

  const runAiOperation = async (operation: string) => {
    if (isGenerating) return;
    setIsGenerating(true);
    setShowAiMenu(false);
    
    // Switch to edit if not already
    setActiveTab('edit');

    const selText = selection.text;
    const fullText = content;
    const isFullReplace = selText.trim() === '';

    const replacementStart = isFullReplace ? content.length : selection.start;
    const replacementEnd = isFullReplace ? content.length : selection.end;

    // We will append/replace based on streaming
    // For simplicity, we'll clear the selection and insert streaming result there
    let generatedChunk = '';

    try {
      const response = await fetch(`/api/v1/workspaces/${workspaceId}/notes/${noteId}/ai`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operation,
          selection: selText,
          full_content: fullText
        })
      });

      if (!response.ok || !response.body) throw new Error('Network error');

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
              if (eventData.event === 'token') {
                const token = eventData.data.text;
                generatedChunk += token;
                
                setContent((prev) => {
                  const before = prev.substring(0, replacementStart);
                  const after = prev.substring(replacementEnd);
                  return before + generatedChunk + after;
                });
              } else if (eventData.event === 'completed') {
                // Done
                setIsGenerating(false);
              }
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            } catch (err) {}
          }
        }
      }
    } catch (err) {
      // eslint-disable-next-line no-console

      setIsGenerating(false);
    }
  };

  const handleSave = async () => {
    await onSave(noteId, content, title);
    // Optionally trigger auto summarize if content changed significantly
  };

  const loadHistory = async () => {
    setShowHistory(true);
    try {
      const res = await fetch(`/api/v1/workspaces/${workspaceId}/notes/${noteId}/versions`);
      const data = await res.json();
      setVersions(data);
    } catch (e) {
      // eslint-disable-next-line no-console

    }
  };

  const restoreVersion = async (version_number: number) => {
    try {
      const res = await fetch(`/api/v1/workspaces/${workspaceId}/notes/${noteId}/versions/restore`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version_number })
      });
      const data = await res.json();
      setContent(data.note.content);
      setShowHistory(false);
    } catch (e) {
      // eslint-disable-next-line no-console

    }
  };

  // Basic [[WikiLink]] parser for Preview
  const renderMarkdown = (text: string) => {
    const processWikiLinks = (str: string) => {
      // Support [[Title|Alias]] and [[Title]]
      return str.replace(/\[\[(.*?)\]\]/g, (match, p1) => {
        const parts = p1.split('|');
        const title = parts[0];
        const alias = parts.length > 1 ? parts[1] : title;
        return `[${alias}](#)`;
      });
    };
    return <ReactMarkdown>{processWikiLinks(text)}</ReactMarkdown>;
  };

  return (
    <div className={`flex flex-col h-full bg-white border border-gray-200 rounded-lg shadow-sm ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-200 bg-gray-50/50">
        <input 
          type="text" 
          value={title} 
          onChange={(e) => setTitle(e.target.value)} 
          placeholder="Note Title"
          className="text-lg font-bold bg-transparent border-none focus:ring-0 text-gray-800 placeholder-gray-400 w-1/2"
        />
        
        <div className="flex items-center gap-2">
          {isGenerating && (
            <span className="text-xs text-primary-600 animate-pulse flex items-center gap-1">
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
              AI Generating...
            </span>
          )}
          <button onClick={() => loadHistory()} className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded" title="Version History">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          </button>
          <button onClick={handleSave} className="px-3 py-1.5 text-xs font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-md transition-colors">
            Save Note
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-4 px-3 py-2 border-b border-gray-200 bg-gray-50 text-sm">
        <div className="flex bg-gray-200/50 rounded-md p-0.5">
          <button 
            onClick={() => setActiveTab('edit')} 
            className={`px-3 py-1 text-xs font-medium rounded ${activeTab === 'edit' ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
          >
            Edit
          </button>
          <button 
            onClick={() => setActiveTab('preview')} 
            className={`px-3 py-1 text-xs font-medium rounded ${activeTab === 'preview' ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
          >
            Preview
          </button>
        </div>
        
        <div className="flex items-center gap-2 border-l border-gray-300 pl-4">
          <span className="text-xs text-gray-400 font-semibold uppercase tracking-wider">AI Tools</span>
          <button onClick={() => runAiOperation('SUMMARIZE')} disabled={isGenerating} className="px-2 py-1 text-xs text-primary-700 bg-primary-50 hover:bg-primary-100 rounded transition-colors disabled:opacity-50">✨ Summarize</button>
          <button onClick={() => runAiOperation('FIND_CITATIONS')} disabled={isGenerating} className="px-2 py-1 text-xs text-primary-700 bg-primary-50 hover:bg-primary-100 rounded transition-colors disabled:opacity-50">✨ Find Citations</button>
        </div>
      </div>

      {/* Editor Area */}
      <div className="flex-1 relative overflow-hidden flex">
        {activeTab === 'edit' ? (
          <textarea
            ref={textareaRef}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onSelect={handleSelect}
            onContextMenu={handleContextMenu}
            className="w-full h-full p-4 resize-none border-none focus:ring-0 text-sm font-mono text-gray-800 leading-relaxed bg-white"
            placeholder="Start writing... Use Markdown. Select text and right-click for AI refinement."
          />
        ) : (
          <div className="w-full h-full p-6 overflow-y-auto prose prose-sm max-w-none bg-white">
            {renderMarkdown(content)}
          </div>
        )}
        
        {/* History Overlay */}
        {showHistory && (
          <div className="absolute inset-y-0 right-0 w-80 bg-white border-l border-gray-200 shadow-2xl flex flex-col z-20 animate-in slide-in-from-right">
            <div className="flex items-center justify-between p-4 border-b border-gray-100">
              <h3 className="font-semibold text-gray-800 text-sm">Version History</h3>
              <button onClick={() => setShowHistory(false)} className="text-gray-400 hover:text-gray-600"><svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg></button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {versions.map(v => (
                <div key={v.id} className="border border-gray-200 rounded p-3 text-xs bg-gray-50 hover:bg-white transition-colors">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-medium text-gray-700">v{v.version_number}</span>
                    <span className="text-gray-400">{new Date(v.created_at).toLocaleString()}</span>
                  </div>
                  <div className="text-gray-500 mb-2 font-mono">By: {v.created_by} | {v.change_type}</div>
                  <button onClick={() => restoreVersion(v.version_number)} className="text-primary-600 hover:text-primary-700 font-medium w-full text-left">Restore this version</button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* AI Context Menu */}
        {showAiMenu && (
          <div 
            className="fixed bg-white border border-gray-200 rounded-lg shadow-xl py-1 z-50 min-w-[150px]"
            style={{ top: menuPosition.top, left: menuPosition.left }}
            role="presentation"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => e.stopPropagation()}
          >
            <div className="px-3 py-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-100">AI Actions</div>
            <button onClick={() => runAiOperation('EXPAND')} className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-primary-50 hover:text-primary-700 transition-colors">✨ Expand</button>
            <button onClick={() => runAiOperation('REFINE')} className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-primary-50 hover:text-primary-700 transition-colors">✨ Refine</button>
            <button onClick={() => runAiOperation('REWRITE')} className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-primary-50 hover:text-primary-700 transition-colors">✨ Rewrite</button>
          </div>
        )}
      </div>
      
      {/* Footer Metadata & Discovery */}
      <div className="px-3 py-3 border-t border-gray-200 bg-gray-50 flex flex-col gap-3">
        {(backlinks.length > 0 || similarNotes.length > 0) && (
          <div className="grid grid-cols-2 gap-4 text-sm mb-2">
            <div>
              <h4 className="font-semibold text-gray-700 text-xs uppercase tracking-wider mb-2">Referenced By</h4>
              <ul className="space-y-2">
                {backlinks.map(bl => (
                  <li key={bl.id} className="text-gray-600 bg-white border border-gray-200 p-2 rounded shadow-sm">
                    <span className="font-medium block text-xs">{bl.title}</span>
                    {bl.excerpt && <span className="text-xs text-gray-400 italic mt-1 block">{bl.excerpt}</span>}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-gray-700 text-xs uppercase tracking-wider mb-2">Related Notes</h4>
              <ul className="space-y-2">
                {similarNotes.map(sn => (
                  <li key={sn.id} className="text-gray-600 bg-white border border-gray-200 p-2 rounded shadow-sm">
                    <span className="font-medium block text-xs">{sn.title}</span>
                    {sn.summary && <span className="text-xs text-gray-400 mt-1 block line-clamp-1">{sn.summary}</span>}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
        
        <div className="text-xs text-gray-400 flex justify-between pt-2 border-t border-gray-200">
          <span>{content.split(/\s+/).filter(Boolean).length} words</span>
          <span>Markdown supported. [[WikiLinks]] supported.</span>
        </div>
      </div>
    </div>
  );
};
