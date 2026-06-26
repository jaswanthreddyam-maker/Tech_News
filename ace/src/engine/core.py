from typing import List, Dict, Type, Any
from ace.src.models.core import ComplianceResult, ComplianceCheck, PluginMetadata
from ace.src.context.providers import RepositoryContext

class Rule:
    """
    An atomic validation rule. Validators register rules with the RuleEngine.
    """
    def __init__(self, id: str, title: str, principle_id: str):
        self.id = id
        self.title = title
        self.principle_id = principle_id

    def evaluate(self, context: RepositoryContext) -> List[ComplianceCheck]:
        raise NotImplementedError("Rules must implement evaluate()")

class Validator:
    """
    A plugin that registers rules. Discovered dynamically by the Registry.
    """
    metadata: PluginMetadata
    depends_on: List[str] = []

    def initialize(self):
        pass

    def discover_rules(self) -> List[Rule]:
        return []

    def cleanup(self):
        pass

class RuleEngine:
    """
    Executes rules against the RepositoryContext, managing dependencies and suppressions.
    """
    def __init__(self, suppressions: Dict[str, Any] = None):
        self.rules: List[Rule] = []
        self.validators: List[Validator] = []
        self.suppressions = suppressions or {}

    def register_validator(self, validator: Validator):
        self.validators.append(validator)

    def execute(self, context: RepositoryContext) -> ComplianceResult:
        # 1. Initialize
        for val in self.validators:
            val.initialize()
            self.rules.extend(val.discover_rules())

        # 2. Evaluate (Simulated DAG for v1.0 Blueprint)
        all_checks: List[ComplianceCheck] = []
        for rule in self.rules:
            # Check suppression
            if rule.id in self.suppressions:
                # Log suppression usage
                continue
            
            checks = rule.evaluate(context)
            all_checks.extend(checks)

        # 3. Cleanup
        for val in self.validators:
            val.cleanup()

        # Score calculation is deferred to the reporter pipeline
        return ComplianceResult(
            score=0.0,
            checks=all_checks,
            repository_version=context.git.get_current_commit(),
            timestamp="now",
            ace_version="1.0"
        )
