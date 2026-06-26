import { Metadata } from "next";
import { notFound } from "next/navigation";
import ArticlePageClient from "./ArticlePageClient";
import { ReadingTracker } from "@/components/reading/tracker";
import { getArticle } from "@/lib/api/fetchers/article";
import { buildArticleMetadata } from "@/lib/metadata/article";
import { NotFoundError } from "@/lib/api/errors";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  try {
    const data = await getArticle(slug);
    return buildArticleMetadata(data.article);
  } catch (e: any) {
    if (e instanceof NotFoundError || e?.status === 404) {
      return { title: "Article Not Found - Tech News Today" };
    }
    return { title: "Tech News Today" };
  }
}

export default async function ArticlePage({ params }: PageProps) {
  const { slug } = await params;

  let data;
  try {
    data = await getArticle(slug);
  } catch (e: any) {
    if (e instanceof NotFoundError || e?.status === 404) {
      notFound();
    }
    // For other errors, let them throw so the ErrorBoundary catches them
    throw e;
  }

  const { article } = data;

  // Inject JSON-LD
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    headline: article.metadata.seoTitle,
    image: article.hero_image || article.thumbnail_url ? [article.hero_image || article.thumbnail_url] : [],
    datePublished: article.publishedAt ? article.publishedAt.toISOString() : undefined,
    author: [{
      "@type": "Organization",
      name: article.sourceName || "Tech News Today",
      url: article.sourceUrl || undefined
    }]
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <ReadingTracker articleId={article.id} contentVersion="v1" />
      <ArticlePageClient article={data} />
    </>
  );
}
