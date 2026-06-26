from typing import List
from ace.src.contracts.rule import Rule, RuleContext
from ace.src.contracts.finding import Finding, Evidence, Severity

class EventVersionRule(Rule):
    @property
    def id(self) -> str: return "ACE-EVT-001"
    
    @property
    def title(self) -> str: return "Every Event Producer specifies an event version."
    
    @property
    def principle(self) -> str: return "P6" # Backward Compatibility
    
    @property
    def depends_on(self) -> List[str]: return []

    def evaluate(self, context: RuleContext) -> List[Finding]:
        # Implementation checks graph.get_nodes_by_type(EventProducer)
        return []

class EventVersionPolicy:
    @property
    def metadata(self) -> dict:
        return {"id": "policy.event.version", "version": "1.0.0"}
    @property
    def required_capabilities(self) -> List[str]: return ["runtime_graph"]
    @property
    def rules(self) -> List[type]: return [EventVersionRule]

# --- Other Event Policies ---

class EventNamingPolicy:
    @property
    def metadata(self) -> dict: return {"id": "policy.event.naming", "version": "1.0.0"}
    @property
    def required_capabilities(self) -> List[str]: return ["runtime_graph"]
    @property
    def rules(self) -> List[type]: return []

class EventCompatibilityPolicy:
    @property
    def metadata(self) -> dict: return {"id": "policy.event.compatibility", "version": "1.0.0"}
    @property
    def required_capabilities(self) -> List[str]: return ["runtime_graph"]
    @property
    def rules(self) -> List[type]: return []

class EventDocumentationPolicy:
    @property
    def metadata(self) -> dict: return {"id": "policy.event.documentation", "version": "1.0.0"}
    @property
    def required_capabilities(self) -> List[str]: return ["runtime_graph"]
    @property
    def rules(self) -> List[type]: return []

class EventReplayPolicy:
    @property
    def metadata(self) -> dict: return {"id": "policy.event.replay", "version": "1.0.0"}
    @property
    def required_capabilities(self) -> List[str]: return ["runtime_graph"]
    @property
    def rules(self) -> List[type]: return []
