import logging
import asyncio
from typing import List, Dict, Any
from app.models.article import ArticleReadModel

logger = logging.getLogger(__name__)

EXECUTIVE_SUMMARY_PROMPT = """
You are an executive technology editor for Tech News Today.
Write a 1 to 2 sentence "Why it matters" executive summary for the following technology article.

STRICT CONSTRAINTS:
- Length: Maximum 45 words, 1-2 sentences.
- Focus: Explain why this story matters strategically to technology, software, hardware, security, or business leaders.
- Accuracy: Do NOT restate the title. Do NOT introduce facts absent from the input data. Do NOT speculate.

Article Title: {title}
Category: {category}
Source: {source}
Summary: {summary}

Output only the 1-2 sentence executive explanation:
"""

class BriefingEnricher:
    """
    Enriches selected briefing articles with 1-2 sentence executive "Why it matters" explanations.
    Implements a strict fail-safe fallback to canonical article summaries if AI fails.
    """

    @classmethod
    async def enrich_item(cls, article: ArticleReadModel) -> str:
        fallback_why = article.summary if article.summary and len(article.summary.strip()) > 10 else f"{article.title}. Key developments published by {article.source or 'Tech News'}."
        
        try:
            import os
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                from google import genai
                client = genai.Client(api_key=api_key)
                prompt = EXECUTIVE_SUMMARY_PROMPT.format(
                    title=article.title,
                    category=article.category or "Technology",
                    source=article.source or "Tech News",
                    summary=article.summary or ""
                )
                loop = asyncio.get_running_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=prompt
                        )
                    ),
                    timeout=4.0
                )
                if response and response.text and len(response.text.strip()) > 10:
                    explanation = response.text.strip().replace('"', '')
                    words = explanation.split()
                    if len(words) > 55:
                        explanation = " ".join(words[:45]) + "..."
                    return explanation
        except Exception as e:
            logger.info(f"BriefingEnricher: Using canonical fallback for article ID {article.id} ({e})")

        return fallback_why

    @classmethod
    async def enrich_articles(
        cls,
        articles: List[ArticleReadModel],
        concurrency: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Enrich a batch of articles in parallel with bounded concurrency.
        Guarantees strict per-item fault isolation: any individual AI timeout or error
        gracefully falls back to the canonical summary without failing the rest of the batch.
        """
        if not articles:
            return []

        sem = asyncio.Semaphore(concurrency)

        async def _enrich_safe(art: ArticleReadModel) -> str:
            async with sem:
                try:
                    return await cls.enrich_item(art)
                except Exception as exc:
                    logger.warning(f"BriefingEnricher: Error during enrich_item for article {art.id}: {exc}")
                    return (
                        art.summary
                        if art.summary and len(art.summary.strip()) > 10
                        else f"{art.title}. Key developments published by {art.source or 'Tech News'}."
                    )

        tasks = [_enrich_safe(art) for art in articles]
        explanations = await asyncio.gather(*tasks, return_exceptions=True)

        enriched_items = []
        for rank, (art, explanation) in enumerate(zip(articles, explanations), 1):
            why_it_matters = (
                str(explanation)
                if isinstance(explanation, str) and len(explanation.strip()) > 0
                else (
                    art.summary
                    if art.summary and len(art.summary.strip()) > 10
                    else f"{art.title}. Key developments published by {art.source or 'Tech News'}."
                )
            )

            article_slug = getattr(art, "slug", None) or getattr(art, "id", "")
            enriched_items.append({
                "rank": rank,
                "article_id": str(art.id),
                "cluster_id": str(getattr(art, "cluster_id", art.id)),
                "headline": art.title,
                "why_it_matters": why_it_matters,
                "category": art.category or "Technology",
                "source": art.source or "Tech News",
                "url": art.url or f"/articles/{article_slug}",
                "read_time": getattr(art, "reading_time", 3) or 3,
            })
        return enriched_items
