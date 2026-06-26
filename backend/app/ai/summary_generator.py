import json
import logging
from datetime import datetime, timezone

from app.schemas.ai_context import AIContext, ContextProfile
from app.schemas.ai_summary import StructuredSummary
from app.ai.schemas import AITaskRequest, ArticleAIInput, AITaskType

logger = logging.getLogger("tech_news.ai_summary")

from app.ai.base_generator import BaseArtifactGenerator


class SummaryGenerator(BaseArtifactGenerator[StructuredSummary]):
    def __init__(self):
        super().__init__(
            artifact_type="SUMMARY", 
            model_schema=StructuredSummary, 
            context_profile=ContextProfile.SUMMARY
        )

    async def _call_llm(self, prompt: str, context: AIContext) -> str:
        prompt_with_schema = (
            f"{prompt}\n\nPlease output valid JSON that strictly matches this format:\n"
            f"{json.dumps(StructuredSummary.model_json_schema())}"
        )
        
        request = AITaskRequest(
            task_type=AITaskType.SUMMARY,
            article=ArticleAIInput(
                title=context.primary_article.title,
                content=context.primary_article.content,
                source=context.primary_article.source_name,
                source_url=getattr(context.primary_article, "url", getattr(context.primary_article, "slug", None))
            ),
            prompt=prompt_with_schema,
            prompt_version="v1",
            prompt_hash="hash_v1",
            model=self.provider.default_model,
            max_output_tokens=4096
        )
        
        response = await self.provider.summarize(request)
        payload = response.payload
        
        # Inject versioning metadata
        if "metadata" not in payload:
            payload["metadata"] = {}
            
        payload["metadata"].update({
            "version": "v2",
            "provider": self.provider.provider_name,
            "model_version": self.provider.default_model,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        })
        
        return json.dumps(payload)
