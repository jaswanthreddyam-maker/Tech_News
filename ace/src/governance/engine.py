from typing import List, Dict, Type
from ace.src.contracts.rule import Rule, RuleContext
from ace.src.contracts.policy import Policy
from ace.src.contracts.finding import Finding
from ace.src.contracts.architecture import ArchitectureModel

class RuleDependencyGraph:
    """
    Computes execution order for Rules and manages skips due to cascaded failures.
    """
    def __init__(self, rules: List[Rule]):
        self.rules = {r.id: r for r in rules}
        self._failures = set()

    def execute_all(self, context: RuleContext) -> List[Finding]:
        all_findings = []
        # In a robust DAG, we would perform topological sort.
        # For Sprint 0.1.1, we assume linear dependency declaration order or simple pass-through.
        for rule_id, rule in self.rules.items():
            skip = False
            for dep in rule.depends_on:
                if dep in self._failures:
                    skip = True
                    break
                    
            if skip:
                continue
                
            findings = rule.evaluate(context)
            all_findings.extend(findings)
            
            # If any finding is a VIOLATION, mark this rule as failed to cascade skips to dependents
            if any(f.severity.name == "VIOLATION" for f in findings):
                self._failures.add(rule.id)
                
        return all_findings

class GovernanceEngine:
    """
    Executes declarative Policies over the ArchitectureModel.
    Produces immutable Findings.
    """
    def __init__(self, policies: List[Policy]):
        self.policies = policies

    def execute(self, model: ArchitectureModel) -> List[Finding]:
        findings = []
        rule_context = RuleContext(architecture=model)
        
        for policy in self.policies:
            # Capability Negotiation could happen here
            
            # Instantiate rules
            rules = [RuleType() for RuleType in policy.rules]
            
            graph = RuleDependencyGraph(rules)
            policy_findings = graph.execute_all(rule_context)
            findings.extend(policy_findings)
            
        return findings
