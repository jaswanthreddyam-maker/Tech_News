from dataclasses import dataclass
from typing import Protocol, Any
from ace.src.contracts.compliance import ComplianceResult

@dataclass(frozen=True)
class Report:
    """
    The unified rendering payload.
    Renderers (HTML, SARIF, JSON) consume this to produce output.
    """
    compliance_result: ComplianceResult
    metrics: dict[str, Any]
    trends: dict[str, Any]

class Renderer(Protocol):
    """
    Transforms the abstract Report into a specific output format.
    """
    def render(self, report: Report) -> str:
        ...
