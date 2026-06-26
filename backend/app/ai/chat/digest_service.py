import json
import logging
import os
import time
from datetime import datetime

from openai import AsyncOpenAI
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chat.digest_context_builder import DigestContextBuilder
from app.ai.chat.digest_strategy import DigestRetrievalStrategy
from app.ai.chat.prompt_registry import ChatPromptRegistry
from app.ai.chat.schemas import ConversationMode
from app.core.config import settings
from app.models.workspace import WorkspaceDigest

logger = logging.getLogger("tech_news.ai.chat.digest_service")


class DigestService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.registry = ChatPromptRegistry()
        api_key = getattr(settings, "OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.chat_model = getattr(settings, "CHAT_MODEL", "gpt-4o-mini")
        self.retrieval_strategy = DigestRetrievalStrategy()
        self.context_builder = DigestContextBuilder()

    async def get_latest_digest(self, workspace_id: int) -> WorkspaceDigest | None:
        stmt = (
            select(WorkspaceDigest)
            .where(WorkspaceDigest.workspace_id == workspace_id)
            .order_by(desc(WorkspaceDigest.created_at))
            .limit(1)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_digests(self, workspace_id: int) -> list[WorkspaceDigest]:
        stmt = (
            select(WorkspaceDigest)
            .where(WorkspaceDigest.workspace_id == workspace_id)
            .order_by(desc(WorkspaceDigest.created_at))
            .limit(20)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def generate_digest_stream(self, workspace_id: int, since_time: datetime, until_time: datetime):
        """
        Yields Server-Sent Events (SSE) while generating the digest, and then saves it to the database.
        """
        start_time = time.time()

        yield f"event: digest_started\ndata: {json.dumps({'status': 'collecting_context'})}\n\n"

        # 1. Retrieve Context
        context_items = await self.retrieval_strategy.retrieve(
            query="digest", db=self.db, workspace_id=workspace_id, since_time=since_time, until_time=until_time
        )

        # Extract metadata payload
        metadata_payload = {}
        cleaned_items = []
        for item in context_items:
            if item.get("type") == "metadata":
                metadata_payload = item.get("payload", {})
            else:
                cleaned_items.append(item)

        yield f"event: context_collected\ndata: {json.dumps(metadata_payload)}\n\n"

        # 2. Build Context Prompt
        system_prompt_content, _ = self.registry.get_prompt(ConversationMode.WORKSPACE_DIGEST)
        final_prompt = self.context_builder.build_context(system_prompt_content, cleaned_items)

        # 3. Stream from LLM
        messages = [
            {"role": "system", "content": final_prompt},
            {"role": "user", "content": "Generate the Daily Digest. Tell me what changed since I last worked."},
        ]

        full_content = ""

        if not self.client:
            yield f"event: error\ndata: {json.dumps({'error': 'AI provider not configured'})}\n\n"
            return

        try:
            stream = await self.client.chat.completions.create(model=self.chat_model, messages=messages, stream=True)
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    text_chunk = chunk.choices[0].delta.content
                    full_content += text_chunk
                    yield f"event: token\ndata: {json.dumps({'text': text_chunk})}\n\n"

            generation_ms = int((time.time() - start_time) * 1000)

            # Save to DB
            digest = WorkspaceDigest(
                workspace_id=workspace_id,
                since_time=since_time,
                until_time=until_time,
                content=full_content,
                status="COMPLETED",
                metadata_payload=metadata_payload,
                generation_ms=generation_ms,
                token_usage=0,  # Could track if needed
            )
            self.db.add(digest)
            await self.db.commit()
            await self.db.refresh(digest)

            yield f"event: completed\ndata: {json.dumps({'id': digest.id, 'status': 'completed'})}\n\n"

        except Exception as e:
            logger.error(f"Error generating digest: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
