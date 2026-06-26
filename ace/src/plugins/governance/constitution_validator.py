import os
import re
from typing import List
from ace.src.engine.core import Rule, Validator
from ace.src.models.core import (
    ComplianceCheck, ComplianceEvidence, Severity, PrincipleDefinition, PluginMetadata
)
from ace.src.context.providers import RepositoryContext

P7_GOVERNANCE_IS_ENFORCEABLE = PrincipleDefinition(
    id="P7",
    weight=15.0,
    title="Governance is Enforceable",
    description="Architectural principles are executable policies, not documentation."
)

class ConstitutionExistsRule(Rule):
    def __init__(self):
        super().__init__(
            id="ACE-CON-001",
            title="Architecture Constitution Exists",
            principle_id="P7"
        )

    def evaluate(self, context: RepositoryContext) -> List[ComplianceCheck]:
        # MarkdownProvider is not fully implemented yet, so we'll check the raw file
        # In a full execution, this would use context.docs
        constitution_path = os.path.join(context.root_dir, "docs", "constitution", "architecture_constitution.md")
        
        if not os.path.exists(constitution_path):
            return [ComplianceCheck(
                id=self.id,
                title=self.title,
                principle=P7_GOVERNANCE_IS_ENFORCEABLE,
                severity=Severity.VIOLATION,
                evidence=ComplianceEvidence(
                    file="docs/constitution/architecture_constitution.md",
                    evidence="The Architecture Constitution file is missing."
                ),
                autofix="Create `docs/constitution/architecture_constitution.md` with the 7 constitutional principles."
            )]
            
        return [ComplianceCheck(
            id=self.id,
            title=self.title,
            principle=P7_GOVERNANCE_IS_ENFORCEABLE,
            severity=Severity.INFO,
            evidence=ComplianceEvidence(
                file="docs/constitution/architecture_constitution.md",
                evidence="Architecture Constitution exists."
            )
        )]

class PrincipleCountRule(Rule):
    def __init__(self):
        super().__init__(
            id="ACE-CON-002",
            title="Constitution Must Have 7 Principles",
            principle_id="P7"
        )

    def evaluate(self, context: RepositoryContext) -> List[ComplianceCheck]:
        constitution_path = os.path.join(context.root_dir, "docs", "constitution", "architecture_constitution.md")
        
        if not os.path.exists(constitution_path):
            return [] # Handled by ACE-CON-001
            
        with open(constitution_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Very simple regex for numbered lists 1-7 in the principles section
        principles_found = len(re.findall(r"^\d+\.\s+\*\*", content, re.MULTILINE))
        
        if principles_found != 7:
             return [ComplianceCheck(
                id=self.id,
                title=self.title,
                principle=P7_GOVERNANCE_IS_ENFORCEABLE,
                severity=Severity.VIOLATION,
                evidence=ComplianceEvidence(
                    file="docs/constitution/architecture_constitution.md",
                    evidence=f"Expected 7 constitutional principles. Found {principles_found}."
                )
            )]
            
        return [ComplianceCheck(
            id=self.id,
            title=self.title,
            principle=P7_GOVERNANCE_IS_ENFORCEABLE,
            severity=Severity.INFO,
            evidence=ComplianceEvidence(
                file="docs/constitution/architecture_constitution.md",
                evidence="Exactly 7 constitutional principles defined."
            )
        )]

class ConstitutionValidator(Validator):
    metadata = PluginMetadata(
        id="validator.governance.constitution",
        name="Constitution Validator",
        version="1.0.0",
        maturity=3
    )

    def discover_rules(self) -> List[Rule]:
        return [ConstitutionExistsRule(), PrincipleCountRule()]
