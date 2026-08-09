import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.getcwd())

from collections import Counter
from app.services.ranking.news_ranking_engine import (
    calculate_impact_score,
    calculate_freshness_score,
    calculate_engagement_score,
    calculate_quality_score,
    calculate_final_score,
)
from app.editorial.ranking import sort_candidates_deterministically
from app.editorial.diversity import apply_diversity_filter
from app.models.article import ArticleReadModel
from pydantic import BaseModel

class MockArticle(BaseModel):
    id: str
    title: str
    source: str
    content: str
    published_at: datetime
    category: str = "Artificial Intelligence"

def build_golden_dataset():
    now = datetime.now(timezone.utc)
    articles = [
        # 1. GPT-6 Launch (Clearly #1)
        MockArticle(
            id="gpt-6-launch",
            title="OpenAI announces GPT-6 model release with massive improvements",
            source="OpenAI Blog",
            content="We are excited to announce gpt-6, a huge step forward in AI. " * 20,
            published_at=now,
        ),
        # 2. Zero-day exploit (Important, no OpenAI mention)
        MockArticle(
            id="zero-day",
            title="Critical zero-day exploit found in popular web servers",
            source="Ars Technica",
            content="A critical zero-day exploit has been discovered affecting thousands of servers. " * 30,
            category="Security",
            published_at=now - timedelta(hours=2),
        ),
        # 3. OpenAI Case study (Mediocre OpenAI)
        MockArticle(
            id="openai-case-study",
            title="How Company X uses OpenAI for better customer service",
            source="OpenAI Blog",
            content="OpenAI helps businesses. Here is a short case study. " * 10,
            published_at=now - timedelta(hours=4),
        ),
        # 4. Another OpenAI story
        MockArticle(
            id="openai-api-update",
            title="Updates to the OpenAI API",
            source="OpenAI Blog",
            content="We are making minor updates to the OpenAI API endpoints.",
            published_at=now - timedelta(hours=6),
        ),
        # 5. TechCrunch on funding
        MockArticle(
            id="startup-funding",
            title="AI startup raises $50M funding round",
            source="TechCrunch",
            content="Another AI startup just raised a large funding round today. " * 20,
            published_at=now - timedelta(hours=1),
        ),
        # 6. TechCrunch on product
        MockArticle(
            id="product-launch",
            title="New productivity tool launches",
            source="TechCrunch",
            content="A new tool is out today to help with productivity.",
            published_at=now - timedelta(hours=8),
        ),
        # 7. Ars Technica general tech
        MockArticle(
            id="ars-general",
            title="The future of processors",
            source="Ars Technica",
            content="Processors are getting faster every year. " * 25,
            published_at=now - timedelta(hours=12),
        ),
        # 8. Google DeepMind
        MockArticle(
            id="deepmind-research",
            title="New research on robotics from Google DeepMind",
            source="Google DeepMind",
            content="Our latest research explores new robotic capabilities using AI models. " * 40,
            published_at=now - timedelta(hours=3),
        ),
        # 9. NVIDIA Blog
        MockArticle(
            id="nvidia-gpus",
            title="NVIDIA announces new data center GPUs",
            source="NVIDIA AI Blog",
            content="NVIDIA continues to push performance with new data center GPUs. " * 15,
            published_at=now - timedelta(hours=5),
        ),
        # 10. The Verge
        MockArticle(
            id="verge-gadget",
            title="Review: The latest smart home gadget",
            source="The Verge",
            content="We tested the new smart home gadget and here is our review. " * 30,
            published_at=now - timedelta(hours=10),
        )
    ]
    return articles

def run_pipeline(articles):
    candidates = []
    article_topics = {}
    for art in articles:
        # Simulate scoring
        impact = calculate_impact_score(art.title, art.category, art.content)
        freshness = calculate_freshness_score(art.published_at)
        engagement = calculate_engagement_score(None, 80)
        quality = calculate_quality_score(art.content, None)
        final = calculate_final_score(impact, freshness, engagement, quality)

        # Map to ArticleReadModel for sort/diversity inputs
        read_model = ArticleReadModel(
            id=art.id,
            title=art.title,
            source=art.source,
            published_at=art.published_at,
            category=art.category,
        )
        
        candidates.append({
            "article": read_model,
            "effective_score": final,
            "impact_score": impact,
            "freshness_multiplier": 1.0,
        })
        article_topics[art.id] = [art.category]
        
    sorted_candidates = sort_candidates_deterministically(candidates)
    selected_items, decisions = apply_diversity_filter(
        sorted_candidates, article_topics, max_total=10
    )
    return selected_items

def test_regression():
    articles = build_golden_dataset()
    selected_items = run_pipeline(articles)
    
    print("\nFINAL HOMEPAGE RANKING:")
    for idx, item in enumerate(selected_items):
        art = item['article']
        print(f"{idx+1}. [{art.source}] {art.title} (Score: {item['effective_score']:.2f})")
        
    # ASSERTIONS
    assert len(selected_items) > 0
    top_id = selected_items[0]["article"].id
    
    # 1. GPT-6 Launch ranks #1
    assert top_id == "gpt-6-launch", f"Expected gpt-6-launch at #1, got {top_id}"
    
    # 2. Zero-day outranks OpenAI Case study
    zero_day_idx = next(i for i, item in enumerate(selected_items) if item["article"].id == "zero-day")
    case_study_idx = next(i for i, item in enumerate(selected_items) if item["article"].id == "openai-case-study")
    assert zero_day_idx < case_study_idx, "Zero-day should outrank mediocre OpenAI case study"
    
    # 3. No more than 3 OpenAI articles
    openai_count = sum(1 for item in selected_items if item["article"].source == "OpenAI Blog")
    assert openai_count <= 3, f"Too many OpenAI articles: {openai_count}"
    
    # 4. At least 3 distinct publishers
    publishers = set(item["article"].source for item in selected_items)
    assert len(publishers) >= 3, f"Not enough publisher diversity: {publishers}"
    
    # 5. HHI < 0.30
    counts = Counter(item["article"].source for item in selected_items)
    hhi = sum((c / len(selected_items))**2 for c in counts.values())
    assert hhi < 0.30, f"HHI too high: {hhi:.4f}"
    
    print("\nALL ASSERTIONS PASSED! ✅")

if __name__ == "__main__":
    test_regression()
