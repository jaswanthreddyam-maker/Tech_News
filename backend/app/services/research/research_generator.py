import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base_generator import BaseArtifactGenerator
from app.schemas.ai_artifacts import AIArtifactStatus, BaseAIArtifact
from app.schemas.ai_context import ResearchContext

logger = logging.getLogger(__name__)

class ResearchArtifactGenerator(BaseArtifactGenerator[BaseAIArtifact]):
    """
    Synthesizes the final ResearchArtifact using the deterministically built ResearchContext.
    """
    async def generate_research(self, session: AsyncSession, article_id: int, research_context: ResearchContext) -> BaseAIArtifact:
        logger.info("ResearchArtifactGenerator: Beginning synthesis for research query.")

        prompt_text = f"Synthesize an answer for the intent {research_context.intent} based on the provided evidence tree."

        # Enforce ADR-0026: If context evidence tree is empty or failed validation, abort.
        if not research_context.evidence_tree:
            raise ValueError("ADR-0026 Violation: Cannot synthesize without evidence.")

        capabilities = self.provider.capabilities
        if capabilities.supports_structured_outputs:
            raw_output = await self._call_llm(prompt_text, research_context)
        else:
            raw_output = await self._call_llm(prompt_text, research_context)

        import json
        try:
            raw_dict = json.loads(raw_output)

            # Subclasses of BaseAIArtifact for ResearchArtifact will have confidence_breakdown
            if "metadata" not in raw_dict:
                 raw_dict["metadata"] = {
                     "version": "1.0",
                     "confidence": research_context.confidence.get("overall", 0.5),
                     "context_version": research_context.metadata.context_version,
                     "model_version": self.config.summary_model,
                     "prompt_version": "v1",
                     "status": AIArtifactStatus.CREATED.value
                 }

            raw_dict["confidence_breakdown"] = research_context.confidence

            artifact = self.model_schema.model_validate(raw_dict)

            artifact = self.repository.version_manager.transition(artifact, AIArtifactStatus.VALIDATING)

            # Synthesizer validation logic
            artifact = self.semantic_validator.validate(artifact)
            artifact = self.citation_validator.validate(artifact, research_context)
            artifact = self.knowledge_validator.validate(artifact)
            artifact = self.normalizer.normalize(artifact)

            artifact = self.repository.version_manager.transition(artifact, AIArtifactStatus.VALIDATED)

            # Cache key uses Snapshot ID and Planner Version
            # In real implementation, pass cache_key down to persistence
            artifact = await self.repository.persist_and_cache(session, artifact, article_id)

        except Exception as e:
            logger.error(f"Research synthesis failed: {e}")
            raise

        return artifact
