from dataclasses import dataclass
from typing import List, Optional, Any
from enum import Enum

class Severity(Enum):
    INFO = 1
    WARNING = 2
    VIOLATION = 3

@dataclass(frozen=True)
class PrincipleDefinition:
    """
    Loaded dynamically from docs/constitution/principles.yaml.
    Represents a core architectural principle and its weighted score.
    """
    id: str
    weight: float
    title: str
    description: str

@dataclass(frozen=True)
class PluginMetadata:
    id: str
    name: str
    version: str
    maturity: int

@dataclass(frozen=True)
class ComplianceEvidence:
    """
    Concrete evidence of a compliance check passing or failing.
    Used heavily for SARIF generation and GitHub annotations.
    """
    file: str
    line: Optional[int] = None
    symbol: Optional[str] = None
    evidence: str = ""

@dataclass(frozen=True)
class ComplianceCheck:
    """
    A single immutable execution result of an ACE Rule.
    """
    id: str
    title: str
    principle: PrincipleDefinition
    severity: Severity
    evidence: Optional[ComplianceEvidence]
    autofix: Optional[str] = None

@dataclass(frozen=True)
class ComplianceResult:
    score: float
    checks: List[ComplianceCheck]
    repository_version: str
    timestamp: str
    ace_version: str
