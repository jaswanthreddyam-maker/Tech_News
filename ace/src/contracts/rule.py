from dataclasses import dataclass
from typing import List, Protocol
from ace.src.contracts.architecture import ArchitectureModel
from ace.src.contracts.finding import Finding

@dataclass(frozen=True)
class RuleContext:
    """
    The scoped context provided to a Rule during execution.
    It exposes the ArchitectureModel, ensuring Rules do not directly touch ASTs.
    """
    architecture: ArchitectureModel

class Rule(Protocol):
    """
    An executable node in the Rule Dependency Graph.
    Must be a pure function: no logging, no state mutation, no I/O writes.
    """
    @property
    def id(self) -> str:
        ...
        
    @property
    def title(self) -> str:
        ...
        
    @property
    def principle(self) -> str:
        ...
        
    @property
    def depends_on(self) -> List[str]:
        ...

    def evaluate(self, context: RuleContext) -> List[Finding]:
        ...
