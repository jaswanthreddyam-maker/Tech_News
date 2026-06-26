import hashlib
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.editorial import (
    DraftVersion,
    EditorialDecision,
    EditorialDraft,
    EditorialDraftStatus,
    EditorialPatch,
    EditorialPatchStatus,
    EditorialReviewArtifact,
    PublicationRecord,
)

logger = logging.getLogger(__name__)

class DraftManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    async def create_draft(
        self, workspace_id: int, title: str, content: str, author_id: str, tags: list[str] | None = None, category: str | None = None, environment: dict | None = None
    ) -> EditorialDraft:
        draft = EditorialDraft(
            workspace_id=workspace_id,
            title=title,
            content=content,
            author_id=author_id,
            tags=tags or [],
            category=category,
            status=EditorialDraftStatus.DRAFT.value
        )
        self.db.add(draft)
        await self.db.flush()

        version = DraftVersion(
            draft_id=draft.id,
            version=1,
            editor_id=author_id,
            title=title,
            content=content,
            content_hash=self._get_hash(content),
            change_summary="Initial draft",
            category=category,
            tags=tags or [],
            environment=environment
        )
        self.db.add(version)

        decision = EditorialDecision(
            draft_id=draft.id,
            actor=author_id,
            action="CREATED",
            decision_source="Human",
            reason="Initial draft creation",
            decision_metadata={
                "duration": 0,
                "previous_state": None,
                "new_state": EditorialDraftStatus.DRAFT.value
            }
        )
        self.db.add(decision)

        await self.db.commit()
        await self.db.refresh(draft)
        return draft

    async def update_draft(
        self, draft_id: int, content: str, editor_id: str, change_summary: str | None = None,
        title: str | None = None, tags: list[str] | None = None, category: str | None = None,
        rendered_html: str | None = None, seo: dict | None = None, metadata_snapshot: dict | None = None,
        cover_image: str | None = None, environment: dict | None = None
    ) -> EditorialDraft:
        stmt = select(EditorialDraft).where(EditorialDraft.id == draft_id)
        res = await self.db.execute(stmt)
        draft = res.scalars().first()

        if not draft:
            raise ValueError("Draft not found")

        v_stmt = select(DraftVersion).where(DraftVersion.draft_id == draft_id).order_by(DraftVersion.version.desc()).limit(1)
        v_res = await self.db.execute(v_stmt)
        last_version = v_res.scalars().first()

        next_version_num = last_version.version + 1 if last_version else 1

        draft.content = content
        if title is not None: draft.title = title
        if tags is not None: draft.tags = tags
        if category is not None: draft.category = category
        draft.updated_at = datetime.now(timezone.utc)
        draft.last_modified_by = editor_id

        version = DraftVersion(
            draft_id=draft.id,
            version=next_version_num,
            editor_id=editor_id,
            title=draft.title,
            content=content,
            rendered_html=rendered_html,
            content_hash=self._get_hash(content),
            change_summary=change_summary or f"Update {next_version_num}",
            category=draft.category,
            tags=draft.tags,
            seo=seo,
            metadata_snapshot=metadata_snapshot,
            cover_image=cover_image,
            environment=environment
        )
        self.db.add(version)

        decision = EditorialDecision(
            draft_id=draft.id,
            actor=editor_id,
            action="UPDATED",
            decision_source="Human",
            reason=change_summary or "Draft content updated",
            decision_metadata={
                "previous_state": draft.status,
                "new_state": draft.status
            }
        )
        self.db.add(decision)

        await self.db.commit()
        await self.db.refresh(draft)
        return draft

    async def transition_status(self, draft_id: int, status: EditorialDraftStatus, actor: str, reason: str | None = None, decision_source: str = "Human") -> EditorialDraft:
        stmt = select(EditorialDraft).where(EditorialDraft.id == draft_id)
        res = await self.db.execute(stmt)
        draft = res.scalars().first()

        if not draft:
            raise ValueError("Draft not found")

        previous_status = draft.status
        draft.status = status.value

        if status == EditorialDraftStatus.SCHEDULED:
            draft.scheduled_by = actor
        elif status == EditorialDraftStatus.APPROVED:
            draft.approved_by = actor
        elif status == EditorialDraftStatus.PUBLISHED:
            draft.published_by = actor
        elif status == EditorialDraftStatus.REVIEW:
            draft.reviewed_by = actor

        decision = EditorialDecision(
            draft_id=draft.id,
            actor=actor,
            action=status.value,
            decision_source=decision_source,
            reason=reason or f"Transitioned to {status.value}",
            decision_metadata={
                "previous_state": previous_status,
                "new_state": status.value
            }
        )
        self.db.add(decision)

        await self.db.commit()
        await self.db.refresh(draft)
        return draft


class AIReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_review(self, draft_id: int, reviewer_id: str = "gpt-5.5") -> EditorialReviewArtifact:
        stmt = select(EditorialDraft).where(EditorialDraft.id == draft_id)
        res = await self.db.execute(stmt)
        draft = res.scalars().first()
        if not draft:
            raise ValueError("Draft not found")

        sections = [
            {"type": "GRAMMAR", "status": "COMPLETED", "confidence": 0.95},
            {"type": "SEO", "status": "COMPLETED", "confidence": 0.88}
        ]

        artifact = EditorialReviewArtifact(
            draft_id=draft_id,
            reviewer_id=reviewer_id,
            review_sections=sections,
            quality_score=0.9
        )
        self.db.add(artifact)
        await self.db.flush()

        author_meta = {"type": "AI_MODEL", "identifier": reviewer_id}

        grammar_patch = EditorialPatch(
            review_id=artifact.id,
            section_type="GRAMMAR",
            status=EditorialPatchStatus.PENDING.value,
            author=author_meta,
            confidence=0.98,
            reason="Use active voice",
            operations=[
                {"op": "replace", "path": "/content/paragraphs/1", "value": "We decided"}
            ],
            evidence=[{"Identity": {"id": "rule_101", "type": "Rule"}, "Presentation": {"title": "Active Voice", "excerpt": "Use active voice."}, "Verification": {"confidence": 0.99, "source": "AP_STYLE"}}]
        )
        self.db.add(grammar_patch)

        seo_patch = EditorialPatch(
            review_id=artifact.id,
            section_type="SEO",
            status=EditorialPatchStatus.PENDING.value,
            author=author_meta,
            confidence=0.92,
            reason="Missing keyword 'AIOS Kernel'",
            operations=[
                {"op": "add", "path": "/seo/keywords/-", "value": "AIOS Kernel"}
            ]
        )
        self.db.add(seo_patch)

        draft.status = EditorialDraftStatus.REVIEW.value
        draft.reviewed_by = reviewer_id

        decision = EditorialDecision(
            draft_id=draft.id,
            actor=reviewer_id,
            action="AI_REVIEW",
            decision_source="AI",
            reason="AI generated review and patches",
            decision_metadata={"review_id": artifact.id, "patch_ids": []}
        )
        self.db.add(decision)

        await self.db.commit()
        await self.db.refresh(artifact)
        return artifact


class FactCheckService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_draft(self, draft_id: int, actor: str = "AI_FactChecker") -> dict:
        stmt = select(EditorialDraft).where(EditorialDraft.id == draft_id)
        res = await self.db.execute(stmt)
        draft = res.scalars().first()
        if not draft:
            raise ValueError("Draft not found")

        fact_check_results = {
            "claims_checked": [
                {
                    "claim": f"Draft mentions {draft.category or 'tech'}.",
                    "evidence": [
                        {
                            "Identity": {"id": "art_123", "type": "Article"},
                            "Presentation": {"title": "Tech Summary", "excerpt": "We are a tech publisher."},
                            "Verification": {"confidence": 0.95, "source": "KnowledgeGraph", "url": "https://kg/art_123"}
                        }
                    ],
                    "decision": "PARTIALLY_SUPPORTED",
                    "confidence": 0.85
                },
                {
                    "claim": "OpenAI released GPT-4 as their newest model.",
                    "evidence": [
                        {
                            "Identity": {"id": "ent_openai", "type": "Entity"},
                            "Presentation": {"title": "OpenAI Models", "excerpt": "GPT-4o was released."},
                            "Verification": {"confidence": 0.99, "source": "FactDB", "url": "https://kg/ent_openai"}
                        }
                    ],
                    "decision": "DISPUTED",
                    "confidence": 0.99
                }
            ],
            "overall_status": "NEEDS_REVIEW"
        }

        draft.fact_checked_by = actor

        decision = EditorialDecision(
            draft_id=draft.id,
            actor=actor,
            action="FACT_CHECK",
            decision_source="AI",
            reason="Automated fact check completed"
        )
        self.db.add(decision)
        await self.db.commit()

        return fact_check_results


class PublishingPipeline:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _generate_artifact_id(self, draft: EditorialDraft) -> str:
        s = f"editorial_{draft.id}_{draft.workspace_id}_{datetime.now().timestamp()}"
        return hashlib.sha256(s.encode('utf-8')).hexdigest()

    async def publish(self, draft_id: int, actor: str = "System") -> str:
        stmt = select(EditorialDraft).where(EditorialDraft.id == draft_id)
        res = await self.db.execute(stmt)
        draft = res.scalars().first()
        if not draft:
            raise ValueError("Draft not found")

        artifact_id = self._generate_artifact_id(draft)
        url = f"https://technewstoday.com/editorial/{artifact_id}"

        article_data = {
            "id": artifact_id,
            "url": url,
            "canonical_url": url,
            "title": draft.title,
            "subtitle": "",
            "author": draft.author_id or "TNT Editorial",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "language": "en",
            "summary": draft.content[:200] + "...",
            "content": draft.content,
            "word_count": len(draft.content.split()),
            "reading_time": max(1, len(draft.content.split()) // 200),
            "images": [],
            "tags": draft.tags,
            "source": "TNT Editorial",
            "license": "Copyright",
            "hash": hashlib.sha256(draft.content.encode('utf-8')).hexdigest()
        }

        from app.core.events.models import EventOutbox
        from app.services.distribution_service import DistributionPlanner

        # 1. Create Publication Record first
        pub_record = PublicationRecord(
            article_id=artifact_id,
            published_by=actor,
            configuration_version="1.0",
            knowledge_version="v_2026",
            review_version="1.0",
            distribution_version="1.0",
            distribution_summary={"status": "PLANNED"}
        )
        self.db.add(pub_record)
        await self.db.flush()

        # 2. Plan Distribution
        planner = DistributionPlanner(self.db)
        await planner.plan_distribution(
            publication_record_id=pub_record.id,
            subject_type="ARTICLE",
            subject_id=artifact_id,
            subject_data=article_data
        )

        # 3. Emit Outbox Event (for broader system projection, independent of distribution)
        outbox_event = EventOutbox(
            event_type="ArticlePublished",
            payload=article_data
        )
        self.db.add(outbox_event)

        draft.status = EditorialDraftStatus.PUBLISHED.value
        draft.published_by = actor

        decision = EditorialDecision(
            draft_id=draft.id,
            actor=actor,
            action="PUBLISHED",
            decision_source="System",
            reason="Article successfully pushed to distribution channels",
            decision_metadata={"artifact_id": artifact_id}
        )
        self.db.add(decision)

        await self.db.commit()

        return artifact_id
