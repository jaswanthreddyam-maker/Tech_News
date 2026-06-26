import re
with open('backend/app/services/workspace_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix workspace_id = 0
create_ws_original = '''        self.db.add(workspace)
        
        await ActivityLogger.log(
            self.db,
            workspace_id=0, # Temporary until flush
            event_type=WorkspaceEventType.WORKSPACE_CREATED,
            actor_type=owner_type,
            resource_type="workspace",
            metadata={"name": name}
        )
        
        await self.db.commit()
        await self.db.refresh(workspace)
        
        # Update the workspace_id on the activity now that we have it
        stmt = select(WorkspaceActivity).where(WorkspaceActivity.workspace_id == 0)
        res = await self.db.execute(stmt)
        act = res.scalars().first()
        if act:
            act.workspace_id = workspace.id
            await self.db.commit()'''

create_ws_fixed = '''        self.db.add(workspace)
        await self.db.flush()
        
        await ActivityLogger.log(
            self.db,
            workspace_id=workspace.id,
            event_type=WorkspaceEventType.WORKSPACE_CREATED,
            actor_type=owner_type,
            resource_type="workspace",
            metadata={"name": name}
        )
        
        await self.db.commit()
        await self.db.refresh(workspace)'''

content = content.replace(create_ws_original, create_ws_fixed)

# Fix asyncio.create_task in add_note
add_note_original = '''        # Trigger embedding in background
        from app.ai.embedding import EmbeddingService
        embedding_service = EmbeddingService()
        asyncio.create_task(embedding_service.process_note_embedding(self.db, wn.id))'''

add_note_fixed = '''        # Trigger embedding in background
        from celery_app import process_note_embedding_task
        process_note_embedding_task.delay(wn.id)'''

content = content.replace(add_note_original, add_note_fixed)

# Fix asyncio.create_task in update_note
update_note_original = '''        # Trigger embedding in background
        from app.ai.embedding import EmbeddingService
        embedding_service = EmbeddingService()
        asyncio.create_task(embedding_service.process_note_embedding(self.db, note.id))'''

update_note_fixed = '''        # Trigger embedding in background
        from celery_app import process_note_embedding_task
        process_note_embedding_task.delay(note.id)'''

content = content.replace(update_note_original, update_note_fixed)

with open('backend/app/services/workspace_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
