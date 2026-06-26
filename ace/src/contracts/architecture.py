from typing import Protocol, List, Any

class ArchitectureModel(Protocol):
    """
    The singular public interface Policies consume.
    Policies NEVER parse ASTs directly. They query this model.
    """
    def events(self) -> List[Any]:
        ...
        
    def health_endpoints(self) -> List[Any]:
        ...
        
    def metrics(self) -> List[Any]:
        ...
        
    def adrs(self) -> List[Any]:
        ...
        
    def event_contracts(self) -> List[Any]:
        ...
        
    def background_jobs(self) -> List[Any]:
        ...
        
    def api_routes(self) -> List[Any]:
        ...
        
    def bounded_contexts(self) -> List[Any]:
        ...
