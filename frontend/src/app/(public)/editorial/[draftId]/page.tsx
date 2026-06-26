"use client";

import { useEffect, useState, use, useCallback } from "react";
import { apiFetch } from "@/lib/api/client";
import { format } from "date-fns";

export default function EditorialEditor({ params }: { params: Promise<{ draftId: string }> }) {
  const { draftId } = use(params);
  const [draft, setDraft] = useState<any>(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // AI Suggestions
  const [review, setReview] = useState<any>(null);
  const [factCheck, setFactCheck] = useState<any>(null);

  const fetchDraft = useCallback(async () => {
    try {
      const data = await apiFetch(`/editorial/drafts/${draftId}`);
      setDraft(data);
      setContent((data as any).content);
      
      // Load latest review if available
      const reviews = (data as any).reviews;
      if (reviews && reviews.length > 0) {
        setReview(reviews[reviews.length - 1].review_payload);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [draftId]);

  useEffect(() => {
    fetchDraft();
  }, [fetchDraft]);
  const handleSave = async (status?: string) => {
    setSaving(true);
    try {
      const body: any = { content };
      if (status) body.status = status;
      
      const data = await apiFetch(`/editorial/drafts/${draftId}`, {
        method: "PUT",
        body: JSON.stringify(body),
      });
      setDraft(data);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const requestAIReview = async () => {
    setSaving(true);
    try {
      const data = await apiFetch(`/editorial/drafts/${draftId}/review`, { method: "POST" });
      setReview((data as any).review_payload);
      await fetchDraft(); // Refresh to get updated status
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const requestFactCheck = async () => {
    setSaving(true);
    try {
      const data = await apiFetch(`/editorial/drafts/${draftId}/fact_check`, { method: "POST" });
      setFactCheck(data);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    if (!confirm("Are you sure you want to publish this draft?")) return;
    setSaving(true);
    try {
      // Must be approved first
      if (draft.status !== "APPROVED") {
        await handleSave("APPROVED");
      }
      await apiFetch(`/editorial/drafts/${draftId}/publish`, { method: "POST" });
      alert("Published successfully!");
      window.location.href = "/editorial";
    } catch (err) {
      console.error(err);
      alert("Failed to publish");
    } finally {
      setSaving(false);
    }
  };

  if (loading || !draft) {
    return <div className="p-8 max-w-6xl mx-auto font-mono text-gray-500">Loading editor...</div>;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 min-h-screen flex gap-6">
      
      {/* Editor Section */}
      <div className="flex-1 flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold font-mono">{draft.title || "Untitled"}</h1>
            <div className="flex items-center gap-2 mt-1">
              <span className={`text-xs px-2 py-0.5 rounded-full font-mono border 
                ${draft.status === "APPROVED" ? "bg-green-50 text-green-700 border-green-200" : 
                  draft.status === "REVIEW" ? "bg-yellow-50 text-yellow-700 border-yellow-200" :
                  "bg-gray-100 text-gray-700 border-gray-200"}`}>
                {draft.status}
              </span>
              <span className="text-xs text-gray-400 font-mono" suppressHydrationWarning>
                Last saved: {format(new Date(draft.updated_at), "MMM d, HH:mm")}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button 
              onClick={() => handleSave()}
              disabled={saving}
              className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              Save Draft
            </button>
            <button 
              onClick={() => handleSave("APPROVED")}
              disabled={saving || draft.status === "APPROVED"}
              className="px-4 py-2 bg-primary-50 text-primary-700 border border-primary-200 rounded-lg text-sm font-medium hover:bg-primary-100 transition-colors disabled:opacity-50"
            >
              Approve
            </button>
            <button 
              onClick={handlePublish}
              disabled={saving || (draft.status !== "APPROVED" && draft.status !== "DRAFT" && draft.status !== "REVIEW")}
              className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              Publish
            </button>
          </div>
        </div>

        <div className="flex-1 border border-gray-200 rounded-xl bg-white shadow-sm overflow-hidden flex flex-col">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="flex-1 w-full p-6 resize-none focus:outline-none text-gray-800 leading-relaxed font-serif text-lg"
            placeholder="Write your story..."
          />
        </div>
      </div>

      {/* AI Assistant Sidebar */}
      <div className="w-80 flex flex-col gap-4">
        <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
          <h3 className="font-semibold text-gray-800 mb-3 font-mono flex justify-between items-center">
            AI Assistant
            <span className="text-xs font-normal text-gray-400">Copilot</span>
          </h3>
          <div className="flex flex-col gap-2">
            <button 
              onClick={requestAIReview}
              disabled={saving}
              className="w-full py-2 bg-gray-50 border border-gray-200 text-gray-700 rounded text-sm hover:bg-gray-100 transition-colors"
            >
              Run Editorial Review
            </button>
            <button 
              onClick={requestFactCheck}
              disabled={saving}
              className="w-full py-2 bg-gray-50 border border-gray-200 text-gray-700 rounded text-sm hover:bg-gray-100 transition-colors"
            >
              Verify Claims (Fact Check)
            </button>
          </div>
        </div>

        {review && (
          <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 shadow-sm flex flex-col gap-3">
            <h4 className="font-semibold text-blue-800 text-sm">Review Suggestions</h4>
            
            <div className="text-xs text-blue-900">
              <span className="font-semibold">Tone:</span> {review.tone}
            </div>
            
            <div className="text-xs text-blue-900">
              <span className="font-semibold">Readability:</span> {review.readability?.score}/10 - {review.readability?.comment}
            </div>

            {review.grammar && review.grammar.length > 0 && (
              <div className="flex flex-col gap-2 mt-2">
                <span className="text-xs font-semibold text-blue-800">Grammar & Style:</span>
                {review.grammar.map((g: any, i: number) => (
                  <div key={i} className="bg-white p-2 rounded border border-blue-200 text-xs">
                    <p className="line-through text-red-500 mb-1">{g.original}</p>
                    <p className="text-green-600 mb-1">{g.replacement}</p>
                    <button 
                      onClick={() => setContent(content.replace(g.original, g.replacement))}
                      className="mt-1 text-[10px] bg-blue-100 text-blue-700 px-2 py-0.5 rounded hover:bg-blue-200"
                    >
                      Accept Change
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {factCheck && (
          <div className="bg-green-50 border border-green-100 rounded-xl p-4 shadow-sm flex flex-col gap-3">
            <h4 className="font-semibold text-green-800 text-sm">Fact Check Results</h4>
            
            <div className="flex flex-col gap-3">
              {factCheck.claims_checked.map((claim: any, i: number) => (
                <div key={i} className="bg-white p-2 rounded border border-green-200 text-xs">
                  <p className="font-medium text-gray-800 mb-1">&quot;{claim.claim}&quot;</p>
                  <p className="text-green-700 font-mono text-[10px] mb-1">Status: {claim.decision} ({(claim.confidence * 100).toFixed(0)}%)</p>
                  <div className="text-[10px] text-gray-500 mt-1">
                    <span className="font-semibold">Evidence:</span> {claim.evidence.join(", ")}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
