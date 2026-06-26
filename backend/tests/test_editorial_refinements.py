import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace
from app.models.distribution import DistributionManifest
from app.models.editorial import DraftVersion, EditorialDraft
from app.services.editorial_service import DraftManager, PublishingPipeline


@pytest.mark.asyncio
async def test_editorial_refinements_workflow(db_session: AsyncSession):
    manager = DraftManager(db_session)
    pipeline = PublishingPipeline(db_session)

    # Explicitly seed the workspace to avoid FK violations
    workspace = Workspace(id=1, name="Test Workspace", owner_id="author_1")
    db_session.add(workspace)
    await db_session.commit()

    # 1. Create Draft
    draft = await manager.create_draft(
        workspace_id=1,
        title="Original Title",
        content="Original Content",
        author_id="author_1",
        tags=["AI"],
        category="Tech",
        environment={"ai_model": "gpt-5.5", "prompt_version": "v1"}
    )
    draft_id = draft.id

    # 2. Make 10 versions
    for i in range(1, 11):
        await manager.update_draft(
            draft_id=draft_id,
            content=f"Content version {i}",
            title=f"Title version {i}",
            editor_id="author_1",
            change_summary=f"Edit {i}",
            environment={"ai_model": "gpt-5.5", "prompt_version": f"v{i+1}"}
        )

    # 3. Publish Draft
    artifact_id = await pipeline.publish(draft_id, actor="System")
    assert artifact_id is not None

    # Verify PublicationRecord
    pub_res = await db_session.execute(
        text("SELECT * FROM publication_records WHERE article_id = :a"),
        {"a": artifact_id}
    )
    pub_record = pub_res.first()
    assert pub_record is not None
    assert pub_record.distribution_summary["status"] == "PLANNED"

    # 4. Reconstruct Draft from versions
    v_stmt = select(DraftVersion).where(DraftVersion.draft_id == draft_id).order_by(DraftVersion.version.asc())
    v_res = await db_session.execute(v_stmt)
    versions = v_res.scalars().all()

    assert len(versions) == 11 # 1 initial + 10 updates

    reconstructed_content = versions[-1].content
    reconstructed_title = versions[-1].title

    # Verify byte-for-byte identical to the draft's current state
    stmt = select(EditorialDraft).where(EditorialDraft.id == draft_id)
    d_res = await db_session.execute(stmt)
    current_draft = d_res.scalars().first()

    assert reconstructed_content == current_draft.content
    assert reconstructed_title == current_draft.title
    assert versions[-1].environment["prompt_version"] == "v11"
