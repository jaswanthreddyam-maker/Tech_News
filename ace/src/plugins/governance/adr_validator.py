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

class ADRDirectoryExistsRule(Rule):
    def __init__(self):
        super().__init__(
            id="ACE-ADR-001",
            title="ADR Directory Must Exist",
            principle_id="P7"
        )

    def evaluate(self, context: RepositoryContext) -> List[ComplianceCheck]:
        adr_path = os.path.join(context.root_dir, "docs", "adrs")
        
        if not os.path.exists(adr_path) or not os.path.isdir(adr_path):
            return [ComplianceCheck(
                id=self.id,
                title=self.title,
                principle=P7_GOVERNANCE_IS_ENFORCEABLE,
                severity=Severity.VIOLATION,
                evidence=ComplianceEvidence(
                    file="docs/adrs/",
                    evidence="The Architecture Decision Records directory is missing."
                ),
                autofix="Create the `docs/adrs/` directory."
            )]
            
        return [ComplianceCheck(
            id=self.id,
            title=self.title,
            principle=P7_GOVERNANCE_IS_ENFORCEABLE,
            severity=Severity.INFO,
            evidence=ComplianceEvidence(
                file="docs/adrs/",
                evidence="ADR directory exists."
            )
        )]

class ADRNumberRule(Rule):
    def __init__(self):
        super().__init__(
            id="ACE-ADR-002",
            title="ADR Files Must Start With 4-Digit Number",
            principle_id="P7"
        )

    def evaluate(self, context: RepositoryContext) -> List[ComplianceCheck]:
        adr_path = os.path.join(context.root_dir, "docs", "adrs")
        checks = []
        
        if not os.path.exists(adr_path):
            return checks # Handled by ACE-ADR-001
            
        for file in os.listdir(adr_path):
            if file.endswith(".md"):
                if not re.match(r"^\d{4}-.+\.md$", file):
                    checks.append(ComplianceCheck(
                        id=self.id,
                        title=self.title,
                        principle=P7_GOVERNANCE_IS_ENFORCEABLE,
                        severity=Severity.VIOLATION,
                        evidence=ComplianceEvidence(
                            file=f"docs/adrs/{file}",
                            evidence=f"ADR filename '{file}' does not match the 4-digit numbering convention."
                        ),
                        autofix=f"Rename '{file}' to 'XXXX-{file}'"
                    ))
        
        if not checks:
            checks.append(ComplianceCheck(
                id=self.id,
                title=self.title,
                principle=P7_GOVERNANCE_IS_ENFORCEABLE,
                severity=Severity.INFO,
                evidence=ComplianceEvidence(
                    file="docs/adrs/",
                    evidence="All ADRs follow the numbering convention."
                )
            ))
            
        return checks

class ADRValidator(Validator):
    metadata = PluginMetadata(
        id="validator.governance.adr",
        name="ADR Validator",
        version="1.0.0",
        maturity=3
    )

    def discover_rules(self) -> List[Rule]:
        return [ADRDirectoryExistsRule(), ADRNumberRule()]
