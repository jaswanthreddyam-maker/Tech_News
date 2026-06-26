from dataclasses import dataclass
from typing import List, Optional
from ace.src.contracts.finding import Severity, Finding

@dataclass(frozen=True)
class TechnicalDebt:
    """
    A managed compliance violation.
    Elevates a raw Finding into a tracked architectural debt entity.
    """
    id: str
    finding: Finding
    principle: str # Will map to ArchitectureID later
    severity: Severity
    documented: bool
    owner: str
    adr: Optional[str] = None
    suppressed: bool = False
    expires: Optional[str] = None
    estimated_effort: Optional[str] = None
    target_release: Optional[str] = None

@dataclass(frozen=True)
class ComplianceResult:
    """
    The calculated compliance state of the repository.
    The Compliance Engine aggregates Findings into TechnicalDebt and hierarchical scores.
    """
    overall_score: float
    grade: str
    technical_debt: List[TechnicalDebt]
    principle_scores: dict[str, float]
    repository_version: str
    timestamp: str
