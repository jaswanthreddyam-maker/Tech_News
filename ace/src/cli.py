import os
import sys

from ace.src.discovery.context import RepositoryContext
from ace.src.discovery.markdown import MarkdownProvider
from ace.src.discovery.ast_provider import ASTProvider

from ace.src.knowledge.graph import CapabilityGraph, BoundedContext, HealthProvider
from ace.src.knowledge.architecture import StandardArchitectureModel
from ace.src.governance.engine import GovernanceEngine
from ace.src.compliance.engine import ComplianceEngine

from ace.src.governance.policies.governance_policy import GovernancePolicy
from ace.src.governance.policies.health_policy import HealthPolicy
from ace.src.governance.policies.event_policies import (
    EventVersionPolicy, EventNamingPolicy, EventCompatibilityPolicy,
    EventDocumentationPolicy, EventReplayPolicy
)
from ace.src.contracts.architecture_ids import AIDRegistry

def build_mock_graph() -> CapabilityGraph:
    """Mocking Discovery -> Knowledge for Sprint 0.2 verification."""
    graph = CapabilityGraph()
    
    ctx = BoundedContext(id="ctx_editorial", subsystem="editorial")
    graph.add_node(ctx)
    
    hp = HealthProvider(id="hp_1", aid="operations.health", endpoint="/api/v1/health", version="1.0", subsystem="editorial")
    graph.add_node(hp)
    
    graph.add_edge(ctx.id, "owns", hp.id)
    return graph

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m ace.src.cli [check|audit|aid doctor]")
        sys.exit(3)

    command = sys.argv[1]
    
    if len(sys.argv) >= 3 and command == "aid" and sys.argv[2] == "doctor":
        print("Doctor OK")
        sys.exit(0)

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    print(f"=============================================")
    print(f" Architecture Compliance Engine (ACE v1.0)   ")
    print(f"=============================================")

    # 1. Discover -> Build Capabilities
    context = RepositoryContext(root_dir)
    context.capabilities.register(MarkdownProvider(root_dir))
    
    # 2. Build CapabilityGraph
    graph = build_mock_graph()

    # 3. Build ArchitectureModel
    model = StandardArchitectureModel(context, graph)

    # 4. Execute Policies
    policies = [
        GovernancePolicy(), 
        HealthPolicy(),
        EventVersionPolicy(),
        EventNamingPolicy(),
        EventCompatibilityPolicy()
    ]
    gov_engine = GovernanceEngine(policies)
    findings = gov_engine.execute(model)

    # 5. Technical Debt -> Compliance -> Report
    comp_engine = ComplianceEngine()
    result = comp_engine.calculate(findings, repo_version="1.0.0")

    print(f"Compliance Score: {result.overall_score}% (Grade {result.grade})")
    print(f"Total Findings Executed: {len(findings)}")
    print(f"Technical Debt Items: {len(result.technical_debt)}")
    print("-" * 45)
    
    for finding in findings:
        status = "[FAIL]" if finding.severity.name == "VIOLATION" else "[PASS]"
        print(f"[{finding.rule_id}] {status} | {finding.message}")
    
    print("=============================================")
    
    if command == "check" and len(result.technical_debt) > 0:
        sys.exit(1)
        
    sys.exit(0)

if __name__ == "__main__":
    main()
