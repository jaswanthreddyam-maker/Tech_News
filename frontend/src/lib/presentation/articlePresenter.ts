import { NormalizedArticle } from "../api/normalizers/article";
import { formatDistanceToNow } from "date-fns";

export interface PresentedArticle extends NormalizedArticle {
  formattedSource: string;
  formattedPublished: string;
  formattedCredibility: string;
  formattedConfidence: string;
  formattedReadingTime: string;
}

export function presentArticle(article: NormalizedArticle): PresentedArticle {
  let formattedPublished = "—";
  if (article.publishedAt) {
    formattedPublished = formatDistanceToNow(article.publishedAt, { addSuffix: true });
  }

  return {
    ...article,
    formattedSource: article.sourceName || "—",
    formattedPublished,
    formattedCredibility: article.credibilityScore !== null ? String(article.credibilityScore) : "—",
    formattedConfidence: article.ai_confidence !== undefined && article.ai_confidence !== null ? String(article.ai_confidence) : "—",
    formattedReadingTime: article.reading_time ? `${article.reading_time} min read` : "—",
  };
}
