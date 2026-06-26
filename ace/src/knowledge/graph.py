from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass(frozen=True)
class GraphNode:
    id: str
    type: str

@dataclass(frozen=True)
class BoundedContext(GraphNode):
    type: str = "BoundedContext"
    subsystem: str = ""

@dataclass(frozen=True)
class HealthProvider(GraphNode):
    type: str = "HealthProvider"
    aid: str = ""
    endpoint: str = ""
    version: str = ""
    subsystem: str = ""

@dataclass(frozen=True)
class EventProducer(GraphNode):
    type: str = "EventProducer"
    event_id: str = ""

@dataclass(frozen=True)
class EventConsumer(GraphNode):
    type: str = "EventConsumer"
    event_id: str = ""

@dataclass(frozen=True)
class MetricProvider(GraphNode):
    type: str = "MetricProvider"
    aid: str = ""
    subsystem: str = ""

@dataclass(frozen=True)
class ReplayCapability(GraphNode):
    type: str = "ReplayCapability"
    handler_id: str = ""

@dataclass
class CapabilityGraph:
    """
    The canonical runtime representation of discovered architecture.
    Policies query this graph instead of directly interacting with the filesystem or AST.
    """
    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    
    # Edges: source_id -> relation_name -> target_ids
    edges: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)

    def add_node(self, node: GraphNode):
        self.nodes[node.id] = node

    def add_edge(self, source_id: str, relation: str, target_id: str):
        if source_id not in self.edges:
            self.edges[source_id] = {}
        if relation not in self.edges[source_id]:
            self.edges[source_id][relation] = []
        self.edges[source_id][relation].append(target_id)

    def get_nodes_by_type(self, type_class: type) -> List[GraphNode]:
        return [n for n in self.nodes.values() if isinstance(n, type_class)]

    def health_providers(self) -> List[HealthProvider]:
        return self.get_nodes_by_type(HealthProvider) # type: ignore

    def bounded_contexts(self) -> List[BoundedContext]:
        return self.get_nodes_by_type(BoundedContext) # type: ignore

    def get_targets(self, source_id: str, relation: str) -> List[GraphNode]:
        if source_id in self.edges and relation in self.edges[source_id]:
            return [self.nodes[t] for t in self.edges[source_id][relation] if t in self.nodes]
        return []
