"""
LayerPolicy — Architectural capability boundary enforcement.

Enforces the frozen architecture dependency graph (Contract 7):

    Domain → depends on nothing external
    Application → depends on Domain (not Infrastructure directly)
    Interface → depends on Application and Domain
    Infrastructure → implements abstractions

Capabilities are mapped to actual source paths, NOT to folder layout.
app/core/ is explicitly NOT a single layer — it contains both domain-level
(events/schemas) and infrastructure-level (database, redis) code.
"""
import ast
import os
from typing import List, Type

from ace.src.contracts.finding import Evidence, Finding, Severity
from ace.src.contracts.rule import Rule, RuleContext


# ---------------------------------------------------------------------------
# Capability → Source Path Mapping
# ---------------------------------------------------------------------------

CAPABILITIES = {
    "domain": {
        "description": "Entities, value objects, domain event schemas",
        "paths": [
            "backend/app/models/",
            "backend/app/schemas/",
        ],
        "forbidden_imports": [
            # Domain must NOT depend on infrastructure details
            "app.core.database",
            "app.core.redis",
            # Domain must NOT depend on application layer
            "app.services.",
            "app.tasks.",
            # Domain must NOT depend on interface layer
            "app.api.",
            "app.cli.",
        ],
    },
    "application": {
        "description": "Application use cases, services, editorial pipelines, tasks",
        "paths": [
            "backend/app/services/",
            "backend/app/editorial/",
            "backend/app/tasks/",
            "backend/app/apps/",
        ],
        "forbidden_imports": [
            # Inversion of control: Application must NOT depend on Interface (API/CLI)
            "app.api.",
            "app.cli.",
        ],
    },
}


def _file_belongs_to_capability(file_path: str, capability_paths: list[str]) -> bool:
    """Check if a file path falls under any of the capability's source paths."""
    normalized = file_path.replace("\\", "/")
    return any(normalized.startswith(p) for p in capability_paths)


def _extract_imports(tree: ast.AST) -> list[tuple[str, int]]:
    """Extract all import module paths with their line numbers from an AST."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append((node.module, node.lineno))
    return imports


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

class LayerDependencyRule(Rule):
    """
    Scans all Python files in capability-mapped paths and checks that their
    imports respect the frozen architecture dependency graph.

    Each violation is reported with:
    - File path and line number
    - The forbidden import statement
    - The source capability and the violated boundary
    """

    @property
    def id(self) -> str:
        return "ACE-LAYER-001"

    @property
    def title(self) -> str:
        return "Architecture Layer Dependency Enforcement"

    @property
    def principle(self) -> str:
        return "P3"  # Structural integrity principle

    @property
    def depends_on(self) -> List[str]:
        return []

    def evaluate(self, context: RuleContext) -> List[Finding]:
        findings = []

        # Access the AST cache through the architecture model's repository context
        # The model stores the RepositoryContext which has registered capability providers
        model = context.architecture
        repo_context = getattr(model, "_context", None)

        if not repo_context:
            return [Finding(
                rule_id=self.id,
                severity=Severity.WARNING,
                evidence=[],
                message="Cannot evaluate layer policy: RepositoryContext not available.",
                recommendation="Ensure the StandardArchitectureModel is initialized with a RepositoryContext.",
            )]

        # Try to get AST data from registered providers
        ast_data = {}
        for provider in getattr(repo_context, "_capabilities", {}).values():
            if hasattr(provider, "capability_type") and provider.capability_type == "ast":
                ast_data = provider.get_data()
                break

        if not ast_data:
            # Try direct AST scanning as fallback
            root_dir = getattr(repo_context, "root_dir", None)
            if root_dir:
                ast_data = self._scan_asts(root_dir)

        if not ast_data:
            return [Finding(
                rule_id=self.id,
                severity=Severity.WARNING,
                evidence=[],
                message="Cannot evaluate layer policy: no AST data available.",
            )]

        # Check each capability's files against its forbidden imports
        for cap_name, cap_config in CAPABILITIES.items():
            cap_paths = cap_config["paths"]
            forbidden = cap_config["forbidden_imports"]

            for file_path, tree in ast_data.items():
                if not _file_belongs_to_capability(file_path, cap_paths):
                    continue

                imports = _extract_imports(tree)
                for import_path, lineno in imports:
                    for forbidden_prefix in forbidden:
                        if import_path.startswith(forbidden_prefix) or import_path == forbidden_prefix.rstrip("."):
                            findings.append(Finding(
                                rule_id=self.id,
                                severity=Severity.VIOLATION,
                                evidence=[Evidence(
                                    file=file_path,
                                    line=lineno,
                                    symbol=import_path,
                                    evidence=(
                                        f"'{cap_name}' layer file imports "
                                        f"'{import_path}' which violates the "
                                        f"architecture dependency graph."
                                    ),
                                )],
                                message=(
                                    f"[{cap_name}] {file_path}:{lineno} imports "
                                    f"'{import_path}' — forbidden by layer policy."
                                ),
                                recommendation=(
                                    f"Move this import to the application/service "
                                    f"layer, or use dependency injection to avoid "
                                    f"the {cap_name}→infrastructure coupling."
                                ),
                            ))

        if not findings:
            findings.append(Finding(
                rule_id=self.id,
                severity=Severity.INFO,
                evidence=[],
                message="All layer dependency constraints satisfied.",
            ))

        return findings

    @staticmethod
    def _scan_asts(root_dir: str) -> dict:
        """Fallback AST scanning when no provider is registered."""
        cache = {}
        target_dir = os.path.join(root_dir, "backend", "app")
        if not os.path.exists(target_dir):
            return cache

        for dirpath, _, filenames in os.walk(target_dir):
            for file in filenames:
                if file.endswith(".py"):
                    full_path = os.path.join(dirpath, file)
                    rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            cache[rel_path] = ast.parse(f.read(), filename=full_path)
                    except Exception:
                        pass
        return cache


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

class LayerPolicy:
    """
    Architectural layer dependency enforcement policy.
    Prevents forbidden imports between capabilities as defined by
    the frozen architecture dependency graph.
    """

    @property
    def metadata(self) -> dict:
        return {
            "name": "LayerPolicy",
            "version": "1.0.0",
            "description": "Enforces architectural capability boundaries via import analysis.",
        }

    @property
    def required_capabilities(self) -> List[str]:
        return ["ast"]

    @property
    def rules(self) -> List[Type[Rule]]:
        return [LayerDependencyRule]
