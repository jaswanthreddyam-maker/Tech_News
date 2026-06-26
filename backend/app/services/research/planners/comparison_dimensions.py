import logging
from typing import Any

logger = logging.getLogger(__name__)

class ComparisonDimension:
    """
    Interface for pluggable comparison dimensions.
    """
    @property
    def name(self) -> str:
        raise NotImplementedError()

    def compare(self, entity_a: Any, entity_b: Any, snapshot_id: int) -> dict[str, Any]:
        raise NotImplementedError()

    def normalize(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        return raw_data

    def evidence(self) -> list[Any]:
        return []

    def confidence(self) -> float:
        return 1.0

class FinancialDimension(ComparisonDimension):
    @property
    def name(self) -> str:
        return "Financial"

    def compare(self, entity_a: Any, entity_b: Any, snapshot_id: int) -> dict[str, Any]:
        return {"a_funding": "$100M", "b_funding": "$200M"}

class LegalDimension(ComparisonDimension):
    @property
    def name(self) -> str:
        return "Legal"

    def compare(self, entity_a: Any, entity_b: Any, snapshot_id: int) -> dict[str, Any]:
        return {"a_lawsuits": 2, "b_lawsuits": 0}

class TimelineDimension(ComparisonDimension):
    @property
    def name(self) -> str:
        return "Timeline"

    def compare(self, entity_a: Any, entity_b: Any, snapshot_id: int) -> dict[str, Any]:
        return {"a_founded": "2010", "b_founded": "2015"}
