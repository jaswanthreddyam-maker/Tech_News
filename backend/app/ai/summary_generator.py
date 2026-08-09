import json
import logging
from datetime import datetime, timezone

from app.schemas.ai_context import AIContext, ContextProfile
from app.schemas.ai_summary import StructuredSummary, DocumentType
from app.ai.schemas import AITaskRequest, ArticleAIInput, AITaskType
from app.ai.document_classifier import detect_document_type
from app.ai.base_generator import BaseArtifactGenerator

logger = logging.getLogger("tech_news.ai_summary")


class SummaryGenerator(BaseArtifactGenerator[StructuredSummary]):
    def __init__(self):
        super().__init__(
            artifact_type="SUMMARY", 
            model_schema=StructuredSummary, 
            context_profile=ContextProfile.SUMMARY
        )

    async def _call_llm(self, prompt: str, context: AIContext) -> str:
        # Step 1: Run fast deterministic classifier (0 token cost, 0ms)
        detected_type, confidence = detect_document_type(
            title=context.primary_article.title,
            content=context.primary_article.content,
            category=context.primary_article.category
        )

        classifier_hint = ""
        if detected_type and confidence >= 0.70:
            classifier_hint = (
                f"\nDETERMINISTIC CLASSIFIER PRE-DETECTION: Detected Document Type = '{detected_type.value}' "
                f"(Confidence: {confidence:.2f})."
            )
            logger.info(
                f"SummaryGenerator: Deterministic classifier pre-detected article as '{detected_type.value}' "
                f"with confidence {confidence:.2f}"
            )

        # Step 2: Build single-pass prompt with explicit title metadata instructions
        prompt_with_schema = (
            f"{prompt}{classifier_hint}\n\n"
            "CRITICAL INSTRUCTIONS FOR SUMMARIZATION:\n"
            "1. THE TITLE IS METADATA ONLY. Never assume the article title represents the entire document.\n"
            "2. Analyze topic distribution across the full body content. Estimate dominant_topic_percentage (0-100%).\n"
            "3. If dominant_topic_percentage < 40%, set is_multi_topic=true and generate a multi-topic collection summary "
            "covering all major sections rather than a single-topic summary.\n\n"
            "Please output valid JSON that strictly matches this format:\n"
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
            prompt_version="v2",
            prompt_hash="hash_v2",
            model=self.provider.default_model,
            max_output_tokens=4096
        )
        
        response = await self.provider.summarize(request)
        payload = response.payload
        
        # Override document_type with deterministic classification if LLM defaulted to breaking_news but deterministic classifier confidence > 0.80
        if detected_type and confidence >= 0.80:
            if payload.get("document_type") in ("breaking_news", "Breaking News"):
                payload["document_type"] = detected_type.value
            if detected_type in (DocumentType.NEWSLETTER, DocumentType.ROUNDUP):
                payload["is_multi_topic"] = True

        # Inject versioning metadata
        if "metadata" not in payload:
            payload["metadata"] = {}
            
        payload["metadata"].update({
            "version": "v2",
            "summary_version": "rc3.2",
            "summary_pipeline": "context-aware-v2",
            "classifier_confidence": confidence if detected_type else 0.0,
            "provider": self.provider.provider_name,
            "model_version": self.provider.default_model,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        })
        
        return json.dumps(payload)
