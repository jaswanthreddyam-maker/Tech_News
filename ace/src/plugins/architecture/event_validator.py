import ast
from typing import List
from ace.src.engine.core import Rule, Validator
from ace.src.models.core import (
    ComplianceCheck, ComplianceEvidence, Severity, PrincipleDefinition, PluginMetadata
)
from ace.src.context.providers import RepositoryContext

P1_CANONICAL_EVENTS = PrincipleDefinition(
    id="P1",
    weight=25.0,
    title="Canonical Events",
    description="Events are the canonical source of truth."
)

class EventVersionRule(Rule):
    def __init__(self):
        super().__init__(
            id="ACE-EVT-001",
            title="Domain Events Must Have Explicit Version",
            principle_id="P1"
        )

    def evaluate(self, context: RepositoryContext) -> List[ComplianceCheck]:
        checks = []
        
        # Scan ALL AST nodes, look for classes ending in "Payload" or "Event"
        for file_path, tree in context.ast._cache.items():
            # Skip non-backend paths for this rule
            if "backend" not in file_path:
                continue
                
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if node.name.endswith("Payload") or node.name.endswith("Event"):
                        has_version = False
                        version_line = None
                        
                        for item in node.body:
                            if isinstance(item, ast.AnnAssign):
                                if isinstance(item.target, ast.Name) and item.target.id == "version":
                                    has_version = True
                                    version_line = item.lineno
                                    break
                            elif isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name) and target.id == "version":
                                        has_version = True
                                        version_line = item.lineno
                                        break
                        
                        if not has_version:
                            checks.append(ComplianceCheck(
                                id=self.id,
                                title=self.title,
                                principle=P1_CANONICAL_EVENTS,
                                severity=Severity.VIOLATION,
                                evidence=ComplianceEvidence(
                                    file=file_path,
                                    line=node.lineno,
                                    symbol=node.name,
                                    evidence=f"Class '{node.name}' lacks a 'version' field."
                                ),
                                autofix=f"Add `version: str = 'v1'` to {node.name}"
                            ))
                        else:
                            checks.append(ComplianceCheck(
                                id=self.id,
                                title=self.title,
                                principle=P1_CANONICAL_EVENTS,
                                severity=Severity.INFO,
                                evidence=ComplianceEvidence(
                                    file=file_path,
                                    line=version_line,
                                    symbol=node.name,
                                    evidence=f"Class '{node.name}' defines 'version'."
                                )
                            ))
        return checks

class EventValidator(Validator):
    metadata = PluginMetadata(
        id="validator.architecture.events",
        name="Event Architecture Validator",
        version="1.0.0",
        maturity=2
    )

    def discover_rules(self) -> List[Rule]:
        return [EventVersionRule()]
