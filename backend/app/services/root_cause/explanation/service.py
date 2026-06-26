import json
import logging
from abc import ABC, abstractmethod
from openai import AsyncOpenAI
from app.core.config import settings
from app.models.telemetry import RootCauseAnalysis, RootCauseExplanation
from app.services.root_cause.explanation.prompts import EXPLANATION_SYSTEM_PROMPT, EXPLANATION_USER_PROMPT
from app.services.root_cause.explanation.schemas import ExplanationOutput
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class BaseExplanationProvider(ABC):
    @abstractmethod
    async def generate_explanation(self, analysis: RootCauseAnalysis) -> RootCauseExplanation:
        pass

class LLMExplanationProvider(BaseExplanationProvider):
    def __init__(self, session: AsyncSession):
        self.session = session
        # Ensure we have an API key; fallback to dummy for local testing if needed
        api_key = settings.OPENAI_API_KEY if settings.OPENAI_API_KEY else "dummy-key"
        self.client = AsyncOpenAI(api_key=api_key)
        self.model_name = "gpt-4o" # default model

    async def generate_explanation(self, analysis: RootCauseAnalysis) -> RootCauseExplanation:
        # Governance Rule: Deterministic confidence must be >= 0.70
        if analysis.confidence_score < 0.70:
            logger.info(f"Skipping AI explanation for analysis {analysis.id}: confidence {analysis.confidence_score} < 0.70")
            explanation_obj = RootCauseExplanation(
                analysis_id=analysis.id,
                summary="Explanation unavailable.",
                explanation="Deterministic confidence below threshold. Manual investigation of the timeline is required.",
                generated_by="Governance Rule",
                model_name="N/A"
            )
            self.session.add(explanation_obj)
            await self.session.commit()
            return explanation_obj

        # Build prompt payload
        factors_str = json.dumps(analysis.confidence_factors, indent=2)
        user_message = EXPLANATION_USER_PROMPT.format(
            root_cause=analysis.root_cause,
            confidence=f"{int(analysis.confidence_score * 100)}%",
            status=analysis.status,
            factors=factors_str
        )

        try:
            response = await self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": EXPLANATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                response_format=ExplanationOutput,
                temperature=0.0
            )
            
            output = response.choices[0].message.parsed
            
            explanation_obj = RootCauseExplanation(
                analysis_id=analysis.id,
                summary=output.summary,
                explanation=f"{output.explanation}\n\nConfidence: {output.confidence_statement}\n\nAction: {output.recommended_action}",
                generated_by="LLMExplanationProvider",
                model_name=self.model_name
            )
            
            self.session.add(explanation_obj)
            await self.session.commit()
            return explanation_obj

        except Exception as e:
            logger.error(f"Failed to generate explanation for analysis {analysis.id}: {e}")
            # Fallback
            explanation_obj = RootCauseExplanation(
                analysis_id=analysis.id,
                summary="Explanation generation failed.",
                explanation=f"An error occurred while communicating with the LLM provider: {str(e)}",
                generated_by="SystemFallback",
                model_name=self.model_name
            )
            self.session.add(explanation_obj)
            await self.session.commit()
            return explanation_obj
