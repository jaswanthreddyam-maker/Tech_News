from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_

from app.core.database import get_db
from app.models.story import StoryDashboardProjection, StoryAssignmentDecision, StoryStatus
from app.models.article import ArticleReadModel
from typing import Any, List

router = APIRouter(prefix="/admin/editorial", tags=["Admin Editorial"])

@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db)):
    """Basic counts for the overview cards."""
    # Active Stories Count
    active_stmt = select(func.count(StoryDashboardProjection.story_id)).where(StoryDashboardProjection.status == "ACTIVE")
    active_count = (await db.execute(active_stmt)).scalar() or 0
    
    # Needs Review Count
    review_stmt = select(func.count(StoryDashboardProjection.story_id)).where(StoryDashboardProjection.editorial_status == "REVIEW")
    review_count = (await db.execute(review_stmt)).scalar() or 0
    
    return {
        "active_stories": active_count,
        "needs_review": review_count,
    }

@router.get("/top-stories")
async def get_top_stories(limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Top stories powered by the CQRS Projection."""
    stmt = select(StoryDashboardProjection).where(
        StoryDashboardProjection.status == "ACTIVE"
    ).order_by(desc(StoryDashboardProjection.unique_readers)).limit(limit)
    
    res = await db.execute(stmt)
    stories = res.scalars().all()
    
    return stories

@router.get("/review-queue")
async def get_review_queue(db: AsyncSession = Depends(get_db)):
    """Unified queue of Article Drafts and Assignment Reviews."""
    # Article Drafts needing review
    drafts_stmt = select(ArticleReadModel).where(ArticleReadModel.editorial_status == "REVIEW").limit(20)
    drafts = (await db.execute(drafts_stmt)).scalars().all()
    
    # Story Assignments needing review
    assignments_stmt = select(StoryAssignmentDecision).where(StoryAssignmentDecision.decision == "EDITOR_REVIEW").limit(20)
    assignments = (await db.execute(assignments_stmt)).scalars().all()
    
    return {
        "article_drafts": drafts,
        "assignment_reviews": assignments
    }

@router.get("/dormant")
async def get_dormant_stories(db: AsyncSession = Depends(get_db)):
    """Includes Reawakening Candidates based on timeline events."""
    stmt = select(StoryDashboardProjection).where(
        StoryDashboardProjection.status == "DORMANT"
    ).order_by(desc(StoryDashboardProjection.last_activity_at)).limit(20)
    
    res = await db.execute(stmt)
    dormant = res.scalars().all()
    
    # In a real app we would join timeline events to highlight Reawakening candidates.
    # For now we'll just return dormant stories.
    return {
        "dormant_stories": dormant,
        "reawakening_candidates": [] # Mocked for RC3.4A initial UI build
    }

from app.models.analytics import CoverageGapAnalytic, StoryTelemetrySnapshot

@router.get("/coverage-gaps")
async def get_coverage_gaps(db: AsyncSession = Depends(get_db)):
    """Formal coverage gap detection based on Demand vs CoverageStrength."""
    stmt = select(CoverageGapAnalytic).order_by(desc(CoverageGapAnalytic.gap_score)).limit(10)
    res = await db.execute(stmt)
    gaps = res.scalars().all()
    
    return {"gaps": gaps}

@router.get("/calibration-status")
async def get_calibration_status(db: AsyncSession = Depends(get_db)):
    """Provides status for Impact Engine RC3.3B Calibration phase."""
    total_snapshots_stmt = select(func.count(StoryTelemetrySnapshot.id))
    total_snapshots = (await db.execute(total_snapshots_stmt)).scalar() or 0
    
    tracked_stories_stmt = select(func.count(StoryDashboardProjection.story_id))
    tracked_stories = (await db.execute(tracked_stories_stmt)).scalar() or 0
    
    return {
        "status": "Collecting Data",
        "observation_window_days_completed": 4, # Mocked for now
        "observation_window_days_total": 7,
        "tracked_stories": tracked_stories,
        "total_snapshots": total_snapshots,
        "expected_activation_date": "2026-07-01" # Fixed date mock for UI
    }

@router.get("/story-graph/{story_id}")
async def get_story_graph(story_id: str, db: AsyncSession = Depends(get_db)):
    """Returns nodes and edges for Story Graph visualization."""
    from app.models.story import RelatedStory
    
    # 1. Fetch Core Story
    story_stmt = select(StoryDashboardProjection).where(StoryDashboardProjection.story_id == story_id)
    story = (await db.execute(story_stmt)).scalar_one_or_none()
    
    if not story:
        return {"nodes": [], "edges": []}
        
    nodes = [{"id": story.story_id, "label": story.title, "type": "story", "is_core": True}]
    edges = []
    
    # 2. Fetch Related Stories
    rel_stmt = select(RelatedStory).where(RelatedStory.source_story_id == story_id)
    relations = (await db.execute(rel_stmt)).scalars().all()
    
    for rel in relations:
        target_stmt = select(StoryDashboardProjection).where(StoryDashboardProjection.story_id == rel.target_story_id)
        target = (await db.execute(target_stmt)).scalar_one_or_none()
        if target:
            nodes.append({"id": target.story_id, "label": target.title, "type": "story", "is_core": False})
            edges.append({"source": story_id, "target": target.story_id, "type": "SIMILAR_TO", "weight": rel.similarity_score})
            
    # 3. Fetch Entities (Mocked for now)
    nodes.extend([
        {"id": "e1", "label": "Artificial Intelligence", "type": "entity"},
        {"id": "e2", "label": "Technology", "type": "entity"}
    ])
    edges.extend([
        {"source": story_id, "target": "e1", "type": "MENTIONS", "weight": 1.0},
        {"source": story_id, "target": "e2", "type": "MENTIONS", "weight": 0.8}
    ])
    
    return {"nodes": nodes, "edges": edges}
