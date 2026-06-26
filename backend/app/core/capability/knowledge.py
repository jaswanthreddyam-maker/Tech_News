import logging
from typing import Any

from app.core.capability.models import CapabilityContract, CapabilityIdentity
from app.core.capability.registry import CapabilityInterface

logger = logging.getLogger(__name__)

def get_knowledge_identity() -> CapabilityIdentity:
    return CapabilityIdentity(
        identity_id="knowledge-system",
        owner="tnt-platform",
        permissions=["read:artifacts", "write:artifacts"]
    )

class EntityExtractionCapability(CapabilityInterface):
    """Extracts Entities from an article."""
    @property
    def contract(self) -> CapabilityContract:
        return CapabilityContract(
            name="EntityExtractionCapability",
            version="v1",
            input_schema={"type": "object", "properties": {"article": {"type": "object"}}},
            output_schema={"type": "array", "items": {"type": "object"}},
            identity=get_knowledge_identity()
        )

    async def execute(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        article = payload.get("article", {})
        title = article.get("title", "").lower()

        # Mocking for architectural validation
        entities = []
        if "apple" in title or "iphone" in title:
            entities.append({
                "id": "company:apple",
                "canonical_name": "Apple Inc.",
                "aliases": ["Apple"],
                "entity_type": "COMPANY",
                "description": "Multinational technology company",
                "confidence": 0.99
            })
            entities.append({
                "id": "product:iphone",
                "canonical_name": "iPhone",
                "aliases": ["Apple iPhone"],
                "entity_type": "PRODUCT",
                "description": "A line of smartphones designed and marketed by Apple Inc.",
                "confidence": 0.98
            })
        else:
            entities.append({
                "id": "company:tech_corp",
                "canonical_name": "Tech Corp",
                "aliases": ["TC"],
                "entity_type": "COMPANY",
                "description": "Generic technology company",
                "confidence": 0.85
            })

        return {"entities": entities}


class EntityExtractionCapabilityV2(CapabilityInterface):
    """Real LLM extraction using Gemini."""
    @property
    def contract(self) -> CapabilityContract:
        return CapabilityContract(
            name="EntityExtractionCapability",
            version="v2",
            input_schema={"type": "object", "properties": {"article": {"type": "object"}}},
            output_schema={"type": "array", "items": {"type": "object"}},
            identity=get_knowledge_identity()
        )

    async def execute(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        article = payload.get("article", {})
        title = article.get("title", "")
        content = article.get("content", "")
        
        from app.ai.providers.factory import build_ai_provider
        from app.ai.schemas import AITaskRequest, ArticleAIInput, AITaskType
        
        provider = build_ai_provider("gemini")
        
        prompt = (
            "Extract the most important named entities (companies, products, people) "
            "from the article. Return a JSON object with an 'entities' array. "
            "Each entity should have: 'id' (format 'type:name'), 'canonical_name', 'aliases' (list), "
            "'entity_type' (COMPANY, PRODUCT, PERSON, OTHER), 'description', and 'confidence' (float 0-1)."
        )
        
        request = AITaskRequest(
            task_type=AITaskType.ENTITIES,
            article=ArticleAIInput(title=title, content=content[:3000]),
            prompt=prompt,
            prompt_version="v2",
            prompt_hash="hash_ent_v2",
            model=provider.default_model,
            max_output_tokens=2048
        )
        
        try:
            response = await provider._call_api(request)
            return response.payload if "entities" in response.payload else {"entities": response.payload}
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return {"entities": []}


class TopicClassificationCapability(CapabilityInterface):
    """Classifies Topics for an article."""
    @property
    def contract(self) -> CapabilityContract:
        return CapabilityContract(
            name="TopicClassificationCapability",
            version="v1",
            input_schema={"type": "object", "properties": {"article": {"type": "object"}}},
            output_schema={"type": "array", "items": {"type": "object"}},
            identity=get_knowledge_identity()
        )

    async def execute(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        article = payload.get("article", {})
        title = article.get("title", "").lower()

        topics = []
        if "apple" in title or "iphone" in title:
            topics.append({
                "name": "Mobile Devices",
                "taxonomy_category": "Mobile",
                "confidence": 0.95
            })
            topics.append({
                "name": "Consumer Electronics",
                "taxonomy_category": "Hardware",
                "confidence": 0.90
            })
        else:
            topics.append({
                "name": "Enterprise Software",
                "taxonomy_category": "Software",
                "confidence": 0.80
            })

        return {"topics": topics}


class TopicClassificationCapabilityV2(CapabilityInterface):
    """Real LLM extraction using Gemini."""
    @property
    def contract(self) -> CapabilityContract:
        return CapabilityContract(
            name="TopicClassificationCapability",
            version="v2",
            input_schema={"type": "object", "properties": {"article": {"type": "object"}}},
            output_schema={"type": "array", "items": {"type": "object"}},
            identity=get_knowledge_identity()
        )

    async def execute(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        article = payload.get("article", {})
        title = article.get("title", "")
        content = article.get("content", "")
        
        from app.ai.providers.factory import build_ai_provider
        from app.ai.schemas import AITaskRequest, ArticleAIInput, AITaskType
        
        provider = build_ai_provider("gemini")
        
        prompt = (
            "Classify the main topics of this article. Return a JSON object with a 'topics' array. "
            "Each topic should have: 'name', 'taxonomy_category' (e.g. Software, Hardware, AI), and 'confidence' (float 0-1). "
            "Keep it to the 3-5 most relevant topics."
        )
        
        request = AITaskRequest(
            task_type=AITaskType.TOPICS,
            article=ArticleAIInput(title=title, content=content[:3000]),
            prompt=prompt,
            prompt_version="v2",
            prompt_hash="hash_top_v2",
            model=provider.default_model,
            max_output_tokens=1024
        )
        
        try:
            response = await provider._call_api(request)
            return response.payload if "topics" in response.payload else {"topics": response.payload}
        except Exception as e:
            logger.error(f"Topic classification failed: {e}")
            return {"topics": []}


class TimelineExtractionCapability(CapabilityInterface):
    """Extracts Timeline Events from an article."""
    @property
    def contract(self) -> CapabilityContract:
        return CapabilityContract(
            name="TimelineExtractionCapability",
            version="v1",
            input_schema={"type": "object", "properties": {"article": {"type": "object"}}},
            output_schema={"type": "array", "items": {"type": "object"}},
            identity=get_knowledge_identity()
        )

    async def execute(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        article = payload.get("article", {})
        title = article.get("title", "").lower()

        events = []
        if "apple" in title or "iphone" in title:
            events.append({
                "event_type": "Product Launch",
                "date": "2026-09",
                "certainty": "HIGH",
                "entities": ["company:apple", "product:iphone"],
                "description": "Apple announces the new iPhone.",
                "confidence": 0.95
            })
        else:
            events.append({
                "event_type": "Funding",
                "date": "2026-06",
                "certainty": "MEDIUM",
                "entities": ["company:tech_corp"],
                "description": "Tech Corp raised Series A.",
                "confidence": 0.80
            })

        return {"events": events}


class RelationshipExtractionCapability(CapabilityInterface):
    """Extracts Relationships between Entities from an article."""
    @property
    def contract(self) -> CapabilityContract:
        return CapabilityContract(
            name="RelationshipExtractionCapability",
            version="v1",
            input_schema={"type": "object", "properties": {"article": {"type": "object"}, "entities": {"type": "array"}}},
            output_schema={"type": "array", "items": {"type": "object"}},
            identity=get_knowledge_identity()
        )

    async def execute(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        article = payload.get("article", {})
        title = article.get("title", "").lower()

        relationships = []
        if "apple" in title or "iphone" in title:
            relationships.append({
                "source": "company:apple",
                "predicate": "RELEASED",
                "target": "product:iphone",
                "confidence": 0.98
            })
        else:
            relationships.append({
                "source": "company:tech_corp",
                "predicate": "FUNDED",
                "target": "company:tech_corp", # Self referencing for mock
                "confidence": 0.80
            })

        return {"relationships": relationships}
