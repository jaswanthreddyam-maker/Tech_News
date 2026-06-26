import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base_generator import BaseArtifactGenerator
from app.schemas.ai_artifacts import AIArtifactStatus, BaseAIArtifact
from app.schemas.ai_context import ResearchContext

logger = logging.getLogger(__name__)

class ComparisonGenerator(BaseArtifactGenerator[BaseAIArtifact]):
    """
    Synthesizes the ComparisonArtifact using pre-computed dimension metrics.
    Strictly adheres to ADR-0029: Generators Never Compute.
    """
    async def generate_research(self, session: AsyncSession, article_id: int, research_context: ResearchContext, workflow_results: dict[str, Any]) -> BaseAIArtifact:
        logger.info("ComparisonGenerator: Beginning synthesis. ADR-0029 enforced.")

        # The LLM prompt focuses solely on formatting and linguistic synthesis of the ALREADY COMPUTED facts.
        prompt_text = (
            "You are a synthesis generator. Transform the following pre-computed comparison dimensions "
            "into a coherent ComparisonArtifact JSON matching the canonical schema. "
            f"Pre-computed Data: {json.dumps(workflow_results)}"
        )

        capabilities = self.provider.capabilities
        if capabilities.supports_structured_outputs:
            raw_output = await self._call_llm(prompt_text, research_context)
        else:
            raw_output = await self._call_llm(prompt_text, research_context)

        try:
            raw_dict = json.loads(raw_output)

            if "metadata" not in raw_dict:
                 raw_dict["metadata"] = {
                     "version": "1.0",
                     "confidence": research_context.confidence.get("overall", 0.8),
                     "context_version": research_context.metadata.context_version,
                     "model_version": self.config.summary_model,
                     "prompt_version": "v1",
                     "status": AIArtifactStatus.CREATED.value
                 }

            # Forward the exact confidence breakdown
            raw_dict["confidence_breakdown"] = research_context.confidence

            artifact = self.model_schema.model_validate(raw_dict)
            artifact = self.repository.version_manager.transition(artifact, AIArtifactStatus.VALIDATING)

            # Validation logic
            artifact = self.semantic_validator.validate(artifact)
            artifact = self.citation_validator.validate(artifact, research_context)
            artifact = self.knowledge_validator.validate(artifact)
            artifact = self.normalizer.normalize(artifact)

            artifact = self.repository.version_manager.transition(artifact, AIArtifactStatus.VALIDATED)

            # Persist
            artifact = await self.repository.persist_and_cache(session, artifact, article_id)

        except Exception as e:
            logger.error(f"Comparison synthesis failed: {e}")
            raise

        return artifact
