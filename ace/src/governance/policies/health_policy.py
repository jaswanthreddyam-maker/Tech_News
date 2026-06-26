from typing import List
from ace.src.contracts.rule import Rule, RuleContext
from ace.src.contracts.finding import Finding, Evidence, Severity

class ContextOwnsOneHealthProviderRule(Rule):
    @property
    def id(self) -> str: return "ACE-HLT-001"
    
    @property
    def title(self) -> str: return "Every bounded context owns exactly one HealthProvider."
    
    @property
    def principle(self) -> str: return "P2" # Observability
    
    @property
    def depends_on(self) -> List[str]: return []

    def evaluate(self, context: RuleContext) -> List[Finding]:
        findings = []
        graph = context.architecture.graph
        contexts = graph.bounded_contexts()
        
        for ctx in contexts:
            providers = graph.get_targets(ctx.id, relation="owns")
            health_providers = [p for p in providers if p.type == "HealthProvider"]
            
            if len(health_providers) == 0:
                findings.append(Finding(
                    rule_id=self.id,
                    severity=Severity.VIOLATION,
                    evidence=[Evidence(file=f"BoundedContext:{ctx.id}")],
                    message=f"Bounded Context '{ctx.subsystem}' does not own a HealthProvider."
                ))
            elif len(health_providers) > 1:
                findings.append(Finding(
                    rule_id=self.id,
                    severity=Severity.VIOLATION,
                    evidence=[Evidence(file=f"BoundedContext:{ctx.id}")],
                    message=f"Bounded Context '{ctx.subsystem}' owns multiple HealthProviders. Exactly 1 is required."
                ))
            else:
                findings.append(Finding(
                    rule_id=self.id,
                    severity=Severity.INFO,
                    evidence=[Evidence(file=f"BoundedContext:{ctx.id}")],
                    message=f"Bounded Context '{ctx.subsystem}' correctly owns one HealthProvider."
                ))
                
        return findings

class HealthProviderMetadataRule(Rule):
    @property
    def id(self) -> str: return "ACE-HLT-002"
    
    @property
    def title(self) -> str: return "Every HealthProvider specifies endpoint, version, subsystem."
    
    @property
    def principle(self) -> str: return "P2"
    
    @property
    def depends_on(self) -> List[str]: return ["ACE-HLT-001"]

    def evaluate(self, context: RuleContext) -> List[Finding]:
        findings = []
        providers = context.architecture.graph.health_providers()
        
        for p in providers:
            if not p.endpoint or not p.version or not p.subsystem or not p.aid:
                findings.append(Finding(
                    rule_id=self.id,
                    severity=Severity.VIOLATION,
                    evidence=[Evidence(file=f"HealthProvider:{p.id}")],
                    message=f"HealthProvider {p.id} is missing required metadata (aid, endpoint, version, subsystem)."
                ))
            else:
                findings.append(Finding(
                    rule_id=self.id,
                    severity=Severity.INFO,
                    evidence=[Evidence(file=f"HealthProvider:{p.id}")],
                    message=f"HealthProvider {p.id} has complete metadata."
                ))
                
        return findings

class HealthPolicy:
    @property
    def metadata(self) -> dict:
        return {"id": "policy.health", "version": "1.0.0"}
        
    @property
    def required_capabilities(self) -> List[str]:
        return ["runtime_graph"] # Demands the graph is populated
        
    @property
    def rules(self) -> List[type]:
        return [ContextOwnsOneHealthProviderRule, HealthProviderMetadataRule]
