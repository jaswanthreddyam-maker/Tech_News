import json
import logging
from datetime import datetime, timezone

from app.ai.base_generator import BaseArtifactGenerator
from app.ai.temporal_engine import TemporalEngine
from app.schemas.ai_artifacts import TimelineArtifact, TimelineEvent
from app.schemas.ai_context import AIContext, ContextProfile

logger = logging.getLogger(__name__)

class TimelineGenerator(BaseArtifactGenerator[TimelineArtifact]):
    def __init__(self):
        super().__init__(
            artifact_type="TIMELINE", 
            model_schema=TimelineArtifact, 
            context_profile=ContextProfile.SUMMARY # Assuming timeline needs similar context scope
        )
        self.temporal_engine = TemporalEngine()

    async def _call_llm(self, prompt: str, context: AIContext) -> str:
        # Mocking LLM extraction of timeline events.
        # In real life, the LLM extracts relative/raw string dates.
        raw_events = [
            {
                "event_id": "1234-5678-90ab",
                "start_time": "Yesterday", # Will be resolved by TemporalEngine
                "end_time": None,
                "precision": "UNKNOWN",
                "title": "Company X Announces New AI Model",
                "description": "Company X released a state-of-the-art model that beats all benchmarks.",
                "confidence": 0.95,
                "citations": ["http://source.com/article1"],
                "entities": ["Company X", "AI"],
                "importance": 0.9
            },
            {
                "event_id": "abcd-efgh-ijkl",
                "start_time": "Q1 2026", # Will be resolved/normalized
                "end_time": None,
                "precision": "UNKNOWN",
                "title": "Beta Testing Began",
                "description": "Initial beta testers received access.",
                "confidence": 0.88,
                "citations": ["http://source.com/article1"],
                "entities": ["Company X"],
                "importance": 0.7
            }
        ]

        # 1. Temporal Resolution
        context_date = datetime.now(timezone.utc)
        resolved_events_dict = self.temporal_engine.process_raw_events(raw_events, context_date)

        # Build raw dict representing TimelineArtifact
        raw_artifact = {
            "metadata": {
                "version": "1.0",
                "confidence": 0.91, # average
                "context_version": context.metadata.context_version,
                "model_version": self.config.summary_model,
                "prompt_version": "v1",
                "status": "CREATED"
            },
            "events": resolved_events_dict
        }

        return json.dumps(raw_artifact)

    async def generate_and_merge(self, session, article_id: int) -> TimelineArtifact:
        """
        Extends the standard generation by adding the cross-article merge stage.
        """
        # Generate single-article timeline
        artifact = await super().generate(session, article_id)

        # Deduplicate intra-article events
        artifact.events = self.temporal_engine.deduplicator.deduplicate(artifact.events)

        # In a real system, we would query the database for existing canonical events
        # related to this topic or entity.
        existing_canonical_events: list[TimelineEvent] = [] 

        # Merge into Canonical Timeline
        artifact.events = self.temporal_engine.cross_merge.merge(existing_canonical_events, artifact.events)

        # Order chronologically
        # Safely sort, handling potential None or missing start_time
        artifact.events.sort(key=lambda e: e.start_time if e.start_time else "")

        return artifact
