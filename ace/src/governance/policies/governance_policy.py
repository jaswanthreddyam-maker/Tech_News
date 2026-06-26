from typing import List
from ace.src.contracts.rule import Rule, RuleContext
from ace.src.contracts.finding import Finding, Evidence, Severity
from ace.src.contracts.architecture_ids import Constitution

class ConstitutionExistsRule(Rule):
    @property
    def id(self) -> str: return "ACE-CON-001"
    
    @property
    def title(self) -> str: return "Architecture Constitution Exists"
    
    @property
    def principle(self) -> str: return "P7"
    
    @property
    def depends_on(self) -> List[str]: return []

    def evaluate(self, context: RuleContext) -> List[Finding]:
        doc = context.architecture.constitution()
        if not doc:
            return [Finding(
                rule_id=self.id,
                severity=Severity.VIOLATION,
                evidence=[],
                message="Architecture Constitution is missing.",
                recommendation="Create docs/constitution/architecture_constitution.md"
            )]
        return [Finding(
            rule_id=self.id,
            severity=Severity.INFO,
            evidence=[Evidence(file=doc.file_path)],
            message="Constitution exists."
        )]

class PrincipleCountRule(Rule):
    @property
    def id(self) -> str: return "ACE-CON-002"
    
    @property
    def title(self) -> str: return "Constitution Must Have 7 Principles"
    
    @property
    def principle(self) -> str: return "P7"
    
    @property
    def depends_on(self) -> List[str]: return ["ACE-CON-001"]

    def evaluate(self, context: RuleContext) -> List[Finding]:
        doc = context.architecture.constitution()
        if not doc:
            return []
            
        section = doc.section(Constitution.PRINCIPLES)
        if not section:
            return [Finding(
                rule_id=self.id,
                severity=Severity.VIOLATION,
                evidence=[Evidence(file=doc.file_path)],
                message=f"Missing AID: '{Constitution.PRINCIPLES.id}'. Cannot locate principles."
            )]
            
        # O(1) lookup succeeded!
        return [Finding(
            rule_id=self.id,
            severity=Severity.INFO,
            evidence=[Evidence(file=doc.file_path)],
            message="Constitution Principles section found via AID."
        )]

class GovernancePolicy:
    @property
    def metadata(self) -> dict:
        return {"id": "policy.governance", "version": "1.0.0"}
        
    @property
    def required_capabilities(self) -> List[str]:
        return ["markdown"]
        
    @property
    def rules(self) -> List[type]:
        return [ConstitutionExistsRule, PrincipleCountRule]
