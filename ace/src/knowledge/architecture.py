from typing import List, Any
import ast
from ace.src.contracts.architecture import ArchitectureModel
from ace.src.discovery.context import RepositoryContext
from ace.src.discovery.document import Document
from ace.src.knowledge.graph import CapabilityGraph

class StandardArchitectureModel(ArchitectureModel):
    """
    The bridge between raw Discovery data (Capabilities) and Governance (Policies).
    Queries the CapabilityGraph.
    """
    def __init__(self, context: RepositoryContext, graph: CapabilityGraph):
        self._context = context
        self._graph = graph
        
        self._ast_cache = self._context.capabilities.get("ast").discover() if self._context.capabilities.has("ast") else {}
        self._docs_cache = self._context.capabilities.get("markdown").discover() if self._context.capabilities.has("markdown") else {}

    @property
    def graph(self) -> CapabilityGraph:
        return self._graph

    def events(self) -> List[tuple[str, ast.ClassDef]]:
        results = []
        for file_path, tree in self._ast_cache.items():
            if "backend" not in file_path:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if node.name.endswith("Payload") or node.name.endswith("Event"):
                        results.append((file_path, node))
        return results

    def adrs(self) -> List[Document]:
        adrs = []
        for file_path, doc in self._docs_cache.items():
            if file_path.startswith("docs/adrs"):
                adrs.append(doc)
        return adrs
        
    def constitution(self) -> Document:
        return self._docs_cache.get("docs/constitution/architecture_constitution.md")

    # Stubbing the rest of the interface
    def health_endpoints(self) -> List[Any]: return []
    def metrics(self) -> List[Any]: return []
    def event_contracts(self) -> List[Any]: return []
    def background_jobs(self) -> List[Any]: return []
    def api_routes(self) -> List[Any]: return []
    def bounded_contexts(self) -> List[Any]: return []
