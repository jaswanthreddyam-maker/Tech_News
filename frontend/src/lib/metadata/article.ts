import { Metadata } from "next";
import { NormalizedArticle } from "../api/normalizers/article";

export function buildArticleMetadata(article: NormalizedArticle): Metadata {
  const images = [article.hero_image, article.thumbnail_url].filter(Boolean) as string[];

  return {
    title: article.metadata.seoTitle,
    description: article.summary || "",
    keywords: article.metadata.seoKeywords,
    openGraph: {
      title: article.metadata.seoTitle,
      description: article.summary || "",
      type: "article",
      publishedTime: article.publishedAt ? article.publishedAt.toISOString() : undefined,
      modifiedTime: article.publishedAt ? article.publishedAt.toISOString() : undefined,
      authors: article.sourceName ? [article.sourceName] : undefined,
      tags: article.whyItMatters || [],
      siteName: "Tech News Today",
      images,
    },
    twitter: {
      card: "summary_large_image",
      title: article.metadata.seoTitle,
      description: article.summary || "",
      images,
    },
    alternates: {
      canonical: `/articles/${article.slug}`,
    }
  };
}
