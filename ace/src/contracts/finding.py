from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

class Severity(Enum):
    INFO = 1
    WARNING = 2
    VIOLATION = 3

@dataclass(frozen=True)
class Evidence:
    """
    Concrete evidence supporting a Finding.
    A single Finding may reference multiple Evidence objects (e.g. an ADR and a source file).
    """
    file: str
    line: Optional[int] = None
    symbol: Optional[str] = None
    evidence: str = ""

@dataclass(frozen=True)
class Finding:
    """
    The immutable output of an executed Rule.
    Findings declare what is wrong; they do not dictate the final compliance score.
    """
    rule_id: str
    severity: Severity
    evidence: List[Evidence]
    message: str
    recommendation: Optional[str] = None
