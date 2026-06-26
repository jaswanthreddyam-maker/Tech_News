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
        for finding in findings:
            if finding.severity.name == "VIOLATION":
                overall_score -= 5.0
                debt_list.append(TechnicalDebt(
                    rule_id=finding.rule_id,
                    severity=finding.severity,
                    documented=False,
                    suppressed=False,
                    adr=None,
                    target_release=None,
                    message=finding.message
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
