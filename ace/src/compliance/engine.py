from typing import List
from ace.src.contracts.finding import Finding
from ace.src.contracts.compliance import ComplianceResult, TechnicalDebt

class ComplianceEngine:
    """
    Transforms immutable Findings into hierarchical compliance states and Technical Debt.
    """
    def calculate(self, findings: List[Finding], repo_version: str) -> ComplianceResult:
        debt_list = []
        overall_score = 100.0
        
        # A simple algorithm for Sprint 0.1.1
        for idx, finding in enumerate(findings):
            if finding.severity.name == "VIOLATION":
                overall_score -= 5.0
                debt_list.append(TechnicalDebt(
                    id=f"TD-{finding.rule_id}-{idx}",
                    finding=finding,
                    principle="P3",
                    severity=finding.severity,
                    documented=False,
                    owner="Architecture Guild",
                    adr=None,
                    suppressed=False,
                    target_release=None
                ))
                
        grade = "A+" if overall_score >= 100.0 else "B" if overall_score >= 90.0 else "F"
        
        return ComplianceResult(
            overall_score=max(0.0, overall_score),
            grade=grade,
            technical_debt=debt_list,
            principle_scores={"P7": 100.0}, # Mocked for now
            repository_version=repo_version,
            timestamp="now"
        )
