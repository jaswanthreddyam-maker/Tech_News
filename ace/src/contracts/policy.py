from typing import List, Protocol, Type
from ace.src.contracts.rule import Rule

class Policy(Protocol):
    """
    Policies are declarative metadata only. They do not execute.
    The Governance Platform uses Policies to build the Rule Dependency Graph.
    """
    @property
    def metadata(self) -> dict:
        ...
        
    @property
    def required_capabilities(self) -> List[str]:
        ...
        
    @property
    def rules(self) -> List[Type[Rule]]:
        ...
