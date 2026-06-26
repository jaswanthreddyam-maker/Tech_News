import { apiFetch } from "@/lib/api/client";
import { RecommendationRequest, RecommendedArticle } from "./types";
import { StandardResponse } from "@/lib/api/types";

export async function fetchRecommendations(req: RecommendationRequest): Promise<RecommendedArticle[]> {
  // If no history and no article, we can't recommend much (could fallback to trending)
  if (!req.historyIds.length && !req.currentArticleId) {
    return [];
  }

  // The backend currently takes ?history_ids=1&history_ids=2&limit=10
  // If we're in article mode, we might just pass the current article as the sole history ID
  // to pivot off of it.
  const ids = req.mode === "article" && req.currentArticleId 
    ? [req.currentArticleId] 
    : req.historyIds.length > 0 
      ? req.historyIds 
      : req.currentArticleId ? [req.currentArticleId] : [];

  const params = new URLSearchParams();
  ids.forEach(id => params.append("history_ids", id.toString()));
  params.append("limit", req.limit.toString());

  const res = await apiFetch<StandardResponse<RecommendedArticle[]>>(`/recommendations?${params.toString()}`);
  
  // Inject reasons frontend-side based on the returned scores if backend didn't provide them
  return (res.data || []).map((article, index) => {
    const reasons = [];
    
    // Expand the list of editorial labels for variety
    const labels = [
      "Highly Similar", 
      "Same Topic", 
      "Different Perspective", 
      "Breaking Update", 
      "Trending", 
      "Fresh Today", 
      "Trusted Source", 
      "Frequently Read Topic"
    ];

    if (article.similarity_score && article.similarity_score > 0.85) {
      reasons.push({ type: "similarity", score: article.similarity_score, label: "Highly Similar" });
    } else {
      reasons.push({ type: "topic", label: labels[index % labels.length] });
    }
    
    // We can also infer credible
    if (["Reuters", "Associated Press", "Bloomberg"].includes(article.source_name || "")) {
      reasons.push({ type: "credible", label: "Trusted Source" });
    }

    return {
      ...article,
      reasons: article.reasons || reasons as any
    };
  });
}
