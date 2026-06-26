import re

with open('backend/celery_app.py', 'r', encoding='utf-8') as f:
    celery_content = f.read()

task_def = '''
@celery_app.task(name="tasks.ai.process_note_embedding_task", bind=True, max_retries=5, default_retry_delay=60)
def process_note_embedding_task(self, note_id: int):
    """
    Asynchronous task to generate vector embeddings for workspace notes.
    """
    import asyncio
    from app.core.database import AsyncSessionLocal
    from app.ai.embedding import EmbeddingService

    logger.info(f"Triggering asynchronous embedding generation for WorkspaceNote ID: {note_id}")

    async def _execute():
        async with AsyncSessionLocal() as db:
            service = EmbeddingService()
            return await service.process_note_embedding(db, note_id)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        res = loop.run_until_complete(_execute())
        logger.info(f"Embedding generation complete for WorkspaceNote ID: {note_id}. Result: {res}")
        return res
    except Exception as exc:
        logger.error(f"Embedding generation failed for WorkspaceNote ID: {note_id}. Error: {exc}")
        retry_delay = self.default_retry_delay * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=retry_delay)
'''

# Avoid double insertion
if "tasks.ai.process_note_embedding_task" not in celery_content:
    celery_content = celery_content.replace(
        '@celery_app.task(name="tasks.images.download_thumbnail")',
        task_def + '\n@celery_app.task(name="tasks.images.download_thumbnail")'
    )
    # Register queue route
    celery_content = celery_content.replace(
        '"tasks.ai.process_embedding_task": {"queue": "embedding_processing"},',
        '"tasks.ai.process_embedding_task": {"queue": "embedding_processing"},\n        "tasks.ai.process_note_embedding_task": {"queue": "embedding_processing"},'
    )
    with open('backend/celery_app.py', 'w', encoding='utf-8') as f:
        f.write(celery_content)

# Fix workspace_service.py imports and usage
with open('backend/app/services/workspace_service.py', 'r', encoding='utf-8') as f:
    ws_content = f.read()

ws_content = ws_content.replace(
    '''        from celery_app import process_note_embedding_task
        process_note_embedding_task.delay(wn.id)''',
    '''        from celery_app import celery_app as celery
        celery.send_task("tasks.ai.process_note_embedding_task", args=[wn.id])'''
)

ws_content = ws_content.replace(
    '''        from celery_app import process_note_embedding_task
        process_note_embedding_task.delay(note.id)''',
    '''        from celery_app import celery_app as celery
        celery.send_task("tasks.ai.process_note_embedding_task", args=[note.id])'''
)

with open('backend/app/services/workspace_service.py', 'w', encoding='utf-8') as f:
    f.write(ws_content)
