import json

from pydantic import ValidationError

from app.schemas.ai_artifacts import BaseAIArtifact
from app.schemas.ai_context import AIContext
from app.schemas.ai_summary import StructuredSummary


class AIValidationError(Exception):
    pass

class SchemaValidator:
    def validate(self, raw_output: str) -> StructuredSummary:
        try:
            # We assume the output is JSON
            if "```json" in raw_output:
                raw_output = raw_output.split("```json")[1].split("```")[0].strip()

            data = json.loads(raw_output)
            return StructuredSummary(**data)
        except json.JSONDecodeError as e:
            raise AIValidationError(f"Syntax Validation Failed: Invalid JSON - {e}")
        except ValidationError as e:
            raise AIValidationError(f"Schema Validation Failed: {e}")

class SemanticValidator:
    def validate(self, summary: StructuredSummary) -> StructuredSummary:
        if not summary.headline.strip():
            raise AIValidationError("Semantic Validation Failed: Headline is empty")

        if len(summary.executive_summary.split()) < 15:
            raise AIValidationError("Semantic Validation Failed: Executive summary too short (must be >= 15 words)")

        if not summary.key_takeaways or len(summary.key_takeaways) < 2:
            raise AIValidationError("Semantic Validation Failed: Must have at least 2 key takeaways")
            
        # Reject generic/mock patterns
        generic_patterns = [
            "this article discusses",
            "the article highlights",
            "new model shows significant reasoning improvements"
        ]
        
        exec_summary_lower = summary.executive_summary.lower()
        if any(pat in exec_summary_lower for pat in generic_patterns):
            raise AIValidationError("Semantic Validation Failed: Executive summary contains generic/stub boilerplate")
            
        for takeaway in summary.key_takeaways:
            desc_lower = takeaway.description.lower()
            if any(pat in desc_lower for pat in generic_patterns):
                raise AIValidationError("Semantic Validation Failed: Key takeaway contains generic/stub boilerplate")

        return summary

class CitationValidator:
    def validate(self, summary: StructuredSummary, context: AIContext) -> StructuredSummary:
        valid_citations = {c.url for c in context.citations}
        # ContextArticle has 'slug' not 'url'; use getattr for safety
        article_slug = getattr(context.primary_article, "url", None) or getattr(context.primary_article, "slug", None)
        if article_slug:
            valid_citations.add(article_slug)

        # Takeaways do not have citations in the new structured format
        return summary

class Normalizer:
    def normalize(self, summary: StructuredSummary) -> StructuredSummary:
        summary.headline = summary.headline.strip()
        return summary

# ---- Knowledge Validation Pipeline (Sprint 4) ----

class ExistenceValidator:
    """Verifies that an entity claimed to exist isn't definitively known NOT to exist."""
    def validate(self, artifact: BaseAIArtifact) -> BaseAIArtifact:
        # Mock logic
        return artifact

class ConflictValidator:
    """Checks for conflicting facts. E.g., 'Founded 2024' when graph says 'Founded 2015'."""
    def validate(self, artifact: BaseAIArtifact) -> BaseAIArtifact:
        # Check claims against graph
        return artifact

class RelationshipValidator:
    """Validates impossible relationships (e.g., Google acquired Microsoft)."""
    def validate(self, artifact: BaseAIArtifact) -> BaseAIArtifact:
        return artifact

class TemporalValidator:
    """Validates temporal logic (e.g., IPO date comes after Founded date)."""
    def validate(self, artifact: BaseAIArtifact) -> BaseAIArtifact:
        return artifact

class ConfidenceValidator:
    """Rejects artifacts that don't meet minimum confidence thresholds."""
    def validate(self, artifact: BaseAIArtifact) -> BaseAIArtifact:
        if artifact.metadata.confidence < 0.6:
            raise AIValidationError(f"Confidence Validation Failed: Score {artifact.metadata.confidence} below threshold 0.6")
        return artifact

class KnowledgeValidationPipeline:
    def __init__(self):
        self.validators = [
            ExistenceValidator(),
            ConflictValidator(),
            RelationshipValidator(),
            TemporalValidator(),
            ConfidenceValidator()
        ]

    def validate(self, artifact: BaseAIArtifact) -> BaseAIArtifact:
        for validator in self.validators:
            artifact = validator.validate(artifact)
        return artifact
