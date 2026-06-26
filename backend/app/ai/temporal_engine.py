import logging
from datetime import datetime
from typing import Any

import dateparser

from app.schemas.ai_artifacts import TemporalPrecision, TimelineEvent

logger = logging.getLogger(__name__)

class TemporalNormalizer:
    """Normalizes resolved datetime objects or strings into strict ISO formats and assigns precision."""
    @staticmethod
    def normalize(date_str: str) -> datetime | None:
        if not date_str:
            return None
        try:
            # We use dateparser for robust fallback if ISO parse fails
            parsed = dateparser.parse(date_str, settings={'TIMEZONE': 'UTC'})
            if parsed:
                return parsed
        except Exception:
            pass
        return None

    @staticmethod
    def assign_precision(date_str: str) -> TemporalPrecision:
        if not date_str:
            return TemporalPrecision.UNKNOWN

        lower = date_str.lower()
        if "q1" in lower or "q2" in lower or "q3" in lower or "q4" in lower:
            return TemporalPrecision.MONTH # typically represents a range of months
        if len(date_str) == 4 and date_str.isdigit():
            return TemporalPrecision.YEAR
        if len(date_str) == 7 and "-" in date_str: # 2024-05
            return TemporalPrecision.MONTH

        return TemporalPrecision.DAY # default fallback

class TemporalResolutionStage:
    """Resolves relative/colloquial dates into concrete dates based on article publish date context."""
    def resolve(self, event: dict[str, Any], context_date: datetime) -> dict[str, Any]:
        raw_start = event.get("start_time")
        if raw_start:
            # If the LLM didn't already resolve it, try to parse it relative to context_date
            # Realistically, the LLM prompt should instruct it to do temporal resolution, 
            # but we can fallback or enforce it here.
            parsed = dateparser.parse(
                raw_start, 
                settings={'RELATIVE_BASE': context_date, 'TIMEZONE': 'UTC'}
            )
            if parsed:
                event["start_time"] = parsed.isoformat()

            # Re-evaluate precision based on the raw string format if the LLM didn't set it
            if "precision" not in event or event["precision"] == TemporalPrecision.UNKNOWN.value:
                event["precision"] = TemporalNormalizer.assign_precision(raw_start)

        raw_end = event.get("end_time")
        if raw_end:
            parsed = dateparser.parse(
                raw_end, 
                settings={'RELATIVE_BASE': context_date, 'TIMEZONE': 'UTC'}
            )
            if parsed:
                event["end_time"] = parsed.isoformat()

        return event

class EventDeduplicator:
    """Merges duplicate events within a single article's timeline."""
    def deduplicate(self, events: list[TimelineEvent]) -> list[TimelineEvent]:
        # Trivial deduplication: merge if start_time and precision match, and titles are very similar.
        unique_events = []
        seen_keys = set()

        for ev in events:
            # Using simple start_time + first 10 chars of title as a naive dedupe key
            # In a real NLP pipeline we'd use semantic similarity (embeddings)
            key = f"{ev.start_time}_{ev.precision.value}_{ev.title[:10].lower()}"
            if key not in seen_keys:
                seen_keys.add(key)
                unique_events.append(ev)
            else:
                logger.info(f"Deduplicator: Dropped intra-article duplicate event '{ev.title}'")
        return unique_events

class CrossArticleMerger:
    """Canonical Timeline Merger. Merges identical events across multiple articles."""
    def merge(self, existing_canonical_events: list[TimelineEvent], new_events: list[TimelineEvent]) -> list[TimelineEvent]:
        # ADR-0019 implementation:
        # Resolves multiple articles describing the same event into one canonical timeline event.
        # This requires checking Time, Extracted Entities, and Embedding Similarity.
        # For this prototype implementation, we do a naive title-word overlap + exact time match.

        merged_results = list(existing_canonical_events)

        for new_ev in new_events:
            is_duplicate = False
            for existing_ev in merged_results:
                if existing_ev.start_time == new_ev.start_time and existing_ev.precision == new_ev.precision:
                    # check entity overlap
                    existing_entities = set([e.lower() for e in existing_ev.entities])
                    new_entities = set([e.lower() for e in new_ev.entities])
                    overlap = existing_entities.intersection(new_entities)

                    if len(overlap) > 0 or existing_ev.title == new_ev.title:
                        # Merge citations
                        existing_ev.citations.extend([c for c in new_ev.citations if c not in existing_ev.citations])
                        # Keep highest confidence and importance
                        existing_ev.confidence = max(existing_ev.confidence, new_ev.confidence)
                        existing_ev.importance = max(existing_ev.importance, new_ev.importance)
                        is_duplicate = True
                        logger.info(f"CrossMerge: Merged '{new_ev.title}' into canonical event {existing_ev.event_id}")
                        break

            if not is_duplicate:
                merged_results.append(new_ev)

        return merged_results

class TemporalEngine:
    def __init__(self):
        self.resolution = TemporalResolutionStage()
        self.deduplicator = EventDeduplicator()
        self.cross_merge = CrossArticleMerger()

    def process_raw_events(self, raw_events: list[dict[str, Any]], context_date: datetime) -> list[TimelineEvent]:
        resolved_events_dict = []
        for raw in raw_events:
            resolved = self.resolution.resolve(raw, context_date)
            resolved_events_dict.append(resolved)

        # The schema parsing will happen inside the Generator, but we can do a quick check
        # Assume at this point the generator uses pydantic to convert Dict -> TimelineEvent

        return resolved_events_dict # Returning Dicts, Generator will instantiate Pydantic models
