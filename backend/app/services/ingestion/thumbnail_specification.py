import json
import logging
from typing import Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)

class AIThumbnailPolicy:
    FORBIDDEN_CATEGORIES = [
        "breaking news",
        "disaster",
        "disasters",
        "conflict",
        "conflicts",
        "crime",
        "war",
        "terrorism"
    ]

    @classmethod
    def is_forbidden(cls, category: str, headline: str) -> bool:
        cat_lower = category.lower() if category else ""
        head_lower = headline.lower() if headline else ""
        
        for fc in cls.FORBIDDEN_CATEGORIES:
            if fc in cat_lower or fc in head_lower:
                return True
        return False

class ThumbnailSpecificationGenerator:
    """
    Interface for generating editorial illustration specifications
    from article metadata.
    
    Returns a dictionary containing:
    - status: "success" | "rejected" | "error"
    - error_type: (optional) str representing the AIThumbnailFailureReason
    - confidence: float
    - reason: str (human readable reason)
    - spec: (optional) Dict containing the specification
    """
    async def generate_specification(self, title: str, summary: str, category: str, source: str) -> Dict[str, Any]:
        raise NotImplementedError()


class GeminiThumbnailSpecificationProvider(ThumbnailSpecificationGenerator):
    def __init__(self):
        try:
            from google import genai
            from app.core.config import settings
            if getattr(settings, "GEMINI_API_KEY", None) == "mock-happy-path":
                self.client = None
                self.model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
            else:
                self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
                self.model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
        except ImportError:
            self.client = None
            logger.warning("google-genai not installed or configured. Gemini spec generator will fail.")

    async def generate_specification(self, title: str, summary: str, category: str, source: str) -> Dict[str, Any]:
        if AIThumbnailPolicy.is_forbidden(category, title):
            return {
                "status": "rejected",
                "confidence": 0.0,
                "reason": "Forbidden by policy",
                "spec": None
            }

        prompt = f"""
        You are an art director for a professional technology news platform.
        We need an editorial illustration specification for an article.
        
        Article Title: {title}
        Article Summary: {summary}
        Category: {category}
        Source: {source}
        
        Generate a JSON specification strictly matching this format:
        {{
            "confidence": <float between 0.0 and 1.0 representing how visual and appropriate this topic is for an illustration>,
            "headline": "<clean headline>",
            "topic": "<broad visual topic>",
            "entities": ["<entity1>", "<entity2>"],
            "visual_elements": ["<element1>", "<element2>"],
            "style": "professional editorial illustration, modern, clean, trustworthy",
            "avoid": ["company logos", "real people", "fake screenshots", "text"]
        }}
        
        Note:
        - If the topic is extremely abstract (like a regulatory filing or API documentation), the confidence should be low (< 0.85).
        - If the topic is highly visual (e.g. quantum computer, new semiconductor, factory, cyberattack), confidence should be high (>= 0.85).
        Return ONLY valid JSON.
        """

        if not self.client:
            from app.core.config import settings
            if getattr(settings, "GEMINI_API_KEY", None) == "mock-happy-path":
                # Special case for end-to-end testing
                pass
            else:
                return {
                    "status": "error",
                    "error_type": "PROVIDER_UNAVAILABLE",
                    "confidence": 0.0,
                    "reason": "No Gemini client",
                    "spec": None
                }

        try:
            from app.core.config import settings
            if getattr(settings, "GEMINI_API_KEY", None) == "mock-happy-path":
                return {
                    "status": "success",
                    "confidence": 0.95,
                    "reason": "Mock happy path execution",
                    "spec": {
                        "headline": title,
                        "topic": "Technology and cybersecurity",
                        "visual_elements": ["abstract tech waves", "security shield"],
                        "style": "clean modern editorial illustration",
                        "avoid": ["text", "words", "gore", "violence"],
                        "confidence": "0.95",
                        "entities": ["Tech", "Cybersecurity"]
                    }
                }
                
            # We must use run_in_executor if google.genai is sync, but let's assume async or use simple sync call for now.
            import asyncio
            loop = asyncio.get_event_loop()
            
            def _call_gemini():
                return self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )

            response = await loop.run_in_executor(None, _call_gemini)
            text = response.text
            
            # Clean up markdown JSON blocks
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
                
            spec = json.loads(text.strip())
            
            confidence = float(spec.get("confidence", 0.0))
            
            return {
                "status": "success",
                "confidence": confidence,
                "reason": f"Generated spec with confidence {confidence}",
                "spec": spec
            }
        except Exception as e:
            logger.error(f"Failed to generate thumbnail specification: {e}", exc_info=True)
            return {
                "status": "error",
                "error_type": "API_ERROR",
                "confidence": 0.0,
                "reason": str(e),
                "spec": None
            }
