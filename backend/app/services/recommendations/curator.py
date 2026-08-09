import logging
from collections import Counter
from app.schemas.recommendations import RecommendationResponse

logger = logging.getLogger("tech_news.editorial.curator")

class EditorialCurator:
    """
    Decoupled Editorial Curation Layer.
    
    Takes candidate recommendations from retrieval strategies (Behavioral, Trending, etc.)
    and applies editorial rules for layout optimization:
    1. Hero selection (prefers verified thumbnails, penalizes imageless self-posts)
    2. Source diversity (soft cap of max 2 articles per source in first N positions)
    3. Duplicate suppression (guarantees strict 0 duplicate article IDs)
    """
    
    @classmethod
    def curate(
        cls,
        candidates: list[RecommendationResponse],
        limit: int = 7,
        max_per_source: int = 2
    ) -> list[RecommendationResponse]:
        if not candidates:
            return []
            
        # Step 1: Duplicate Suppression (Strict deduplication by article ID)
        seen_ids = set()
        unique_candidates: list[RecommendationResponse] = []
        for c in candidates:
            art_id = str(c.article.get("id") or c.article.get("slug"))
            if art_id not in seen_ids:
                seen_ids.add(art_id)
                unique_candidates.append(c)
                
        if not unique_candidates:
            return []

        # Step 2: Score candidates for HERO placement (Position 0)
        def compute_hero_score(item: RecommendationResponse) -> float:
            art = item.article
            base_score = float(item.score or 0.5)
            
            # Check thumbnail availability
            hero_img = art.get("hero_image") or art.get("thumbnail_local") or art.get("thumbnail_url")
            has_thumbnail = bool(hero_img and "fallback" not in str(hero_img).lower() and "placeholder" not in str(hero_img).lower())
            
            # Source characteristics
            src_name = (art.get("source_name") or art.get("source") or "").lower()
            is_community_selfpost = "reddit" in src_name or "hacker news" in src_name
            
            hero_score = base_score
            if has_thumbnail:
                hero_score += 0.35  # Major boost for verified thumbnail
            else:
                hero_score -= 0.30  # Penalty for imageless hero candidate
                
            if is_community_selfpost and not has_thumbnail:
                hero_score -= 0.20  # Additional penalty for imageless Reddit self-posts
                
            return hero_score

        # Find best candidate for Hero (Position 0)
        hero_candidate = max(unique_candidates, key=compute_hero_score)
        
        # Step 3: Curate remaining items enforcing source diversity
        remaining_pool = [c for c in unique_candidates if c != hero_candidate]
        
        curated: list[RecommendationResponse] = [hero_candidate]
        source_counts = Counter([hero_candidate.article.get("source_name") or hero_candidate.article.get("source") or "Unknown"])
        
        # First Pass: Fill slots respecting source diversity cap & preferring thumbnails
        deferred_items: list[RecommendationResponse] = []
        
        # Sort remaining by score + thumbnail preference
        def compute_secondary_score(item: RecommendationResponse) -> float:
            art = item.article
            hero_img = art.get("hero_image") or art.get("thumbnail_local") or art.get("thumbnail_url")
            has_thumb = bool(hero_img and "fallback" not in str(hero_img).lower())
            return (item.score or 0.5) + (0.1 if has_thumb else 0.0)

        remaining_pool.sort(key=compute_secondary_score, reverse=True)

        for item in remaining_pool:
            if len(curated) >= limit:
                break
            src = item.article.get("source_name") or item.article.get("source") or "Unknown"
            if source_counts[src] < max_per_source:
                source_counts[src] += 1
                curated.append(item)
            else:
                deferred_items.append(item)
                
        # Second Pass: If slots are not filled, backfill from deferred candidates
        if len(curated) < limit and deferred_items:
            for item in deferred_items:
                if len(curated) >= limit:
                    break
                curated.append(item)
                
        logger.info(
            f"EditorialCurator: Curated {len(curated)} items from {len(candidates)} candidates. "
            f"Hero='{hero_candidate.article.get('title')[:40]}' (source={hero_candidate.article.get('source_name')})"
        )
        
        return curated[:limit]
