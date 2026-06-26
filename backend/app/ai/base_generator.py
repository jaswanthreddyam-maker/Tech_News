import json
import logging
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.config import AIConfig
from app.ai.prompts.registry import PromptTemplateRegistry
from app.ai.providers.factory import build_ai_provider
from app.ai.validation import (
    AIValidationError,
    CitationValidator,
    KnowledgeValidationPipeline,
    Normalizer,
    SchemaValidator,
    SemanticValidator,
)
from app.schemas.ai_artifacts import AIArtifactStatus, BaseAIArtifact
from app.schemas.ai_context import AIContext, ContextProfile, PrivacyLevel
from app.services.ai.artifact_repository import ArtifactRepository
from app.services.ai.context_builder import AIContextBuilder

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseAIArtifact)

class BaseArtifactGenerator(Generic[T]):
    def __init__(self, artifact_type: str, model_schema: type[T], context_profile: ContextProfile):
        self.artifact_type = artifact_type
        self.model_schema = model_schema
        self.context_profile = context_profile

        self.config = AIConfig()
        self.provider = build_ai_provider(self.config.providers[0])
        self.repository = ArtifactRepository()

        self.schema_validator = SchemaValidator()
        self.semantic_validator = SemanticValidator()
        self.citation_validator = CitationValidator()
        self.knowledge_validator = KnowledgeValidationPipeline()
        self.normalizer = Normalizer()

    async def generate(self, session: AsyncSession, article_id: int) -> T:
        logger.info(f"{self.__class__.__name__}: Beginning generation for article {article_id}")

        context_builder = AIContextBuilder()
        context = await context_builder.build(
            session=session, 
            article_id=article_id, 
            privacy_level=PrivacyLevel.PUBLIC
        )
        context.metadata.context_profile = self.context_profile

        prompt_template = PromptTemplateRegistry.get(self.artifact_type, "v1")
        if not prompt_template:
            prompt_text = f"Generate {self.artifact_type} based on context."
        else:
            prompt_text = prompt_template.render(context.to_prompt_string())

        capabilities = self.provider.capabilities
        if capabilities.supports_structured_outputs or capabilities.supports_json_mode:
            raw_output = await self._call_llm(prompt_text, context)
        else:
            raw_output = await self._call_llm(prompt_text, context)

        try:
            raw_dict = json.loads(raw_output)
            if "metadata" not in raw_dict:
                 raw_dict["metadata"] = {
                     "version": "1.0",
                     "confidence": 0.9,
                     "context_version": context.metadata.context_version,
                     "model_version": self.config.summary_model,
                     "prompt_version": "v1",
                     "status": AIArtifactStatus.CREATED.value
                 }

            artifact = self.model_schema.model_validate(raw_dict)

            # Transition to VALIDATING
            artifact = self.repository.version_manager.transition(artifact, AIArtifactStatus.VALIDATING)

            # Core Validation
            artifact = self.semantic_validator.validate(artifact)
            artifact = self.citation_validator.validate(artifact, context)

            # Knowledge Validation
            artifact = self.knowledge_validator.validate(artifact)

            # Normalize
            artifact = self.normalizer.normalize(artifact)

            # Transition to VALIDATED
            artifact = self.repository.version_manager.transition(artifact, AIArtifactStatus.VALIDATED)

            # Persist and transition to ACTIVE
            artifact = await self.repository.persist_and_cache(session, artifact, article_id)

        except AIValidationError as e:
            logger.error(f"Validation failed for {self.artifact_type}: {e!s}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in generation: {e}")
            raise

        return artifact

    async def _call_llm(self, prompt: str, context: AIContext) -> str:
        raise NotImplementedError("Subclasses must implement _call_llm")
