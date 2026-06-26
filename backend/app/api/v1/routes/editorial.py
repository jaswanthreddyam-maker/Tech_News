from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.editorial import DiscussionThread, DraftComment, EditorialDraft, EditorialDraftStatus, EditorialPatch
from app.models.user import User
from app.schemas.editorial import (
    CommentCreate,
    DiscussionThreadResponse,
    DraftCommentResponse,
    EditorialDraftCreate,
    EditorialDraftResponse,
    EditorialDraftUpdate,
    EditorialPatchResponse,
    EditorialReviewResponse,
    FactCheckResponse,
    PatchUpdate,
    PublishResponse,
    ThreadCreate,
)
from app.services.editorial_service import AIReviewService, DraftManager, FactCheckService, PublishingPipeline

router = APIRouter()

@router.post("/drafts", response_model=EditorialDraftResponse, status_code=status.HTTP_201_CREATED)
async def create_draft(
    draft_in: EditorialDraftCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    manager = DraftManager(db)
    author_id = draft_in.author_id or current_user.id
    draft = await manager.create_draft(
        workspace_id=draft_in.workspace_id,
        title=draft_in.title,
        content=draft_in.content,
        author_id=str(author_id),
        tags=draft_in.tags,
        category=draft_in.category
    )
    return await get_draft(draft.id, db, current_user)

@router.get("/drafts", response_model=list[EditorialDraftResponse])
async def list_drafts(
    workspace_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.models.editorial import EditorialReviewArtifact
    stmt = select(EditorialDraft).options(
        selectinload(EditorialDraft.versions),
        selectinload(EditorialDraft.reviews).selectinload(EditorialReviewArtifact.patches),
        selectinload(EditorialDraft.threads).selectinload(DiscussionThread.comments)
    )
    if workspace_id:
        stmt = stmt.where(EditorialDraft.workspace_id == workspace_id)

    res = await db.execute(stmt)
    return res.scalars().unique().all()

@router.get("/drafts/{draft_id}", response_model=EditorialDraftResponse)
async def get_draft(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.models.editorial import EditorialReviewArtifact
    stmt = select(EditorialDraft).options(
        selectinload(EditorialDraft.versions),
        selectinload(EditorialDraft.reviews).selectinload(EditorialReviewArtifact.patches),
        selectinload(EditorialDraft.threads).selectinload(DiscussionThread.comments)
    ).where(EditorialDraft.id == draft_id)

    res = await db.execute(stmt)
    draft = res.scalars().first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft

@router.put("/drafts/{draft_id}", response_model=EditorialDraftResponse)
async def update_draft(
    draft_id: int,
    draft_in: EditorialDraftUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    manager = DraftManager(db)

    if draft_in.content is not None or draft_in.title is not None:
        await manager.update_draft(
            draft_id=draft_id,
            content=draft_in.content if draft_in.content is not None else "",
            editor_id=str(draft_in.editor_id or current_user.id),
            change_summary=draft_in.change_summary,
            title=draft_in.title,
            tags=draft_in.tags,
            category=draft_in.category,
            rendered_html=draft_in.rendered_html,
            seo=draft_in.seo,
            metadata_snapshot=draft_in.metadata_snapshot,
            cover_image=draft_in.cover_image,
            environment=draft_in.environment
        )

    if draft_in.status is not None:
        status_enum = EditorialDraftStatus(draft_in.status)
        await manager.transition_status(
            draft_id, 
            status_enum, 
            actor=str(draft_in.editor_id or current_user.id), 
            reason=draft_in.change_summary
        )

    return await get_draft(draft_id, db, current_user)

@router.post("/drafts/{draft_id}/review", response_model=EditorialReviewResponse)
async def request_review(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    review_service = AIReviewService(db)
    try:
        review = await review_service.generate_review(draft_id)
        from app.models.editorial import EditorialReviewArtifact
        stmt = select(EditorialReviewArtifact).options(selectinload(EditorialReviewArtifact.patches)).where(EditorialReviewArtifact.id == review.id)
        res = await db.execute(stmt)
        return res.scalars().first()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/drafts/{draft_id}/fact_check", response_model=FactCheckResponse)
async def fact_check(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fc_service = FactCheckService(db)
    try:
        result = await fc_service.check_draft(draft_id, actor="AI_FactChecker")
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/drafts/{draft_id}/publish", response_model=PublishResponse)
async def publish_draft(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pipeline = PublishingPipeline(db)
    try:
        artifact_id = await pipeline.publish(draft_id, actor=str(current_user.id))
        return PublishResponse(
            status="success",
            artifact_id=artifact_id,
            message="Draft published successfully to ArticleArtifact and projected."
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Threads and Comments endpoints
@router.post("/drafts/{draft_id}/threads", response_model=DiscussionThreadResponse)
async def create_thread(
    draft_id: int,
    thread_in: ThreadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    thread = DiscussionThread(
        draft_id=draft_id,
        anchor=thread_in.anchor,
        resolved=False
    )
    db.add(thread)
    await db.flush()

    comment = DraftComment(
        thread_id=thread.id,
        author_id=str(current_user.id),
        content=thread_in.content
    )
    db.add(comment)
    await db.commit()

    stmt = select(DiscussionThread).options(selectinload(DiscussionThread.comments)).where(DiscussionThread.id == thread.id)
    res = await db.execute(stmt)
    return res.scalars().first()

@router.post("/drafts/{draft_id}/threads/{thread_id}/comments", response_model=DraftCommentResponse)
async def add_comment_to_thread(
    draft_id: int,
    thread_id: int,
    comment_in: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    comment = DraftComment(
        thread_id=thread_id,
        author_id=str(current_user.id),
        content=comment_in.content
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment

@router.patch("/drafts/{draft_id}/threads/{thread_id}/resolve", response_model=DiscussionThreadResponse)
async def resolve_thread(
    draft_id: int,
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(DiscussionThread).options(selectinload(DiscussionThread.comments)).where(DiscussionThread.id == thread_id, DiscussionThread.draft_id == draft_id)
    res = await db.execute(stmt)
    thread = res.scalars().first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    thread.resolved = True
    thread.closed_by = str(current_user.id)
    thread.closed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(thread)
    return thread

@router.patch("/drafts/{draft_id}/patches/{patch_id}", response_model=EditorialPatchResponse)
async def update_patch(
    draft_id: int,
    patch_id: int,
    patch_in: PatchUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(EditorialPatch).where(EditorialPatch.id == patch_id)
    res = await db.execute(stmt)
    patch = res.scalars().first()
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")

    patch.status = patch_in.status
    if patch_in.reason:
        patch.reason = patch_in.reason

    if patch_in.status == "ACCEPTED":
        patch.accepted_by = str(current_user.id)
        patch.accepted_at = datetime.now(timezone.utc)

    patch.updated_at = datetime.now(timezone.utc)

    from app.models.editorial import EditorialDecision
    decision = EditorialDecision(
        draft_id=draft_id,
        actor=str(current_user.id),
        action=f"PATCH_{patch.status}",
        decision_source="Human",
        reason=f"Patch {patch_id} was {patch.status}. {patch_in.reason or ''}",
        decision_metadata={"patch_id": patch_id}
    )
    db.add(decision)

    await db.commit()
    await db.refresh(patch)
    return patch
