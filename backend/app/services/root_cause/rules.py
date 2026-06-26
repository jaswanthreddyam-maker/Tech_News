from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.models.telemetry import TimelineNode, TimelineNodeType

class ConfidenceFactor:
    def __init__(self, evidence: str, weight: float):
        self.evidence = evidence
        self.weight = weight
        
    def to_dict(self) -> dict:
        return {"evidence": self.evidence, "weight": self.weight}

class RuleEvaluationResult:
    def __init__(self, is_match: bool, root_cause: str = "", confidence_score: float = 0.0, factors: List[ConfidenceFactor] = None, status: str = "OPEN"):
        self.is_match = is_match
        self.root_cause = root_cause
        self.confidence_score = confidence_score
        self.factors = factors or []
        self.status = status

class BaseRootCauseRule(ABC):
    """
    Evaluates a causal chain of TimelineNodes to deterministically identify a root cause.
    """
    @abstractmethod
    def evaluate(self, nodes: List[TimelineNode]) -> RuleEvaluationResult:
        pass

class CQRSProjectionLagRule(BaseRootCauseRule):
    def evaluate(self, nodes: List[TimelineNode]) -> RuleEvaluationResult:
        factors = []
        score = 0.0
        
        has_lag = False
        triggered = False
        succeeded = False
        failed = False
        
        for node in nodes:
            if node.node_type == TimelineNodeType.HEALTH_CHECK.value and "CQRS" in node.title:
                has_lag = True
                factors.append(ConfidenceFactor(evidence="CQRS Projection Lag Detected", weight=0.4))
                score += 0.4
            elif node.node_type == TimelineNodeType.RECOVERY.value and "Triggered" in node.title and "CQRS" in node.title:
                triggered = True
                factors.append(ConfidenceFactor(evidence="CQRS Recovery Triggered", weight=0.3))
                score += 0.3
            elif node.node_type == TimelineNodeType.RECOVERY.value and "Succeeded" in node.title and "CQRS" in node.title:
                succeeded = True
                factors.append(ConfidenceFactor(evidence="CQRS Recovery Succeeded", weight=0.3))
                score += 0.3
            elif node.node_type == TimelineNodeType.RECOVERY.value and "Failed" in node.title and "CQRS" in node.title:
                failed = True
                factors.append(ConfidenceFactor(evidence="CQRS Recovery Failed", weight=0.1))
                score += 0.1
                
        if has_lag and triggered:
            status = "AUTO_RESOLVED" if succeeded else ("MANUAL_REQUIRED" if failed else "OPEN")
            return RuleEvaluationResult(
                is_match=True,
                root_cause="CQRS Projection Lag",
                confidence_score=min(1.0, round(score, 2)),
                factors=factors,
                status=status
            )
            
        return RuleEvaluationResult(is_match=False)

class WorkerOfflineRule(BaseRootCauseRule):
    def evaluate(self, nodes: List[TimelineNode]) -> RuleEvaluationResult:
        factors = []
        score = 0.0
        
        has_offline = False
        failed = False
        disabled = False
        
        for node in nodes:
            # We look for indications of worker downtime or Kill Switch activation
            if node.node_type == TimelineNodeType.HEALTH_CHECK.value and "offline" in str(node.description).lower():
                has_offline = True
                factors.append(ConfidenceFactor(evidence="Worker Offline Detected", weight=0.8))
                score += 0.8
            elif node.node_type == TimelineNodeType.ALERT.value and "Kill Switch" in node.title:
                disabled = True
                factors.append(ConfidenceFactor(evidence="Automation Kill Switch Activated", weight=0.4))
                score += 0.4
            elif node.node_type == TimelineNodeType.RECOVERY.value and "Failed" in node.title:
                failed = True
                factors.append(ConfidenceFactor(evidence="Recovery Failed", weight=0.2))
                score += 0.2
                
        if disabled or has_offline:
            return RuleEvaluationResult(
                is_match=True,
                root_cause="Worker Infrastructure Offline",
                confidence_score=min(1.0, round(score, 2)),
                factors=factors,
                status="MANUAL_REQUIRED"
            )
            
        return RuleEvaluationResult(is_match=False)

class ThumbnailFailureRule(BaseRootCauseRule):
    def evaluate(self, nodes: List[TimelineNode]) -> RuleEvaluationResult:
        factors = []
        score = 0.0
        
        has_failure = False
        succeeded = False
        
        for node in nodes:
            if node.node_type == TimelineNodeType.HEALTH_CHECK.value and "THUMBNAIL" in node.title:
                has_failure = True
                factors.append(ConfidenceFactor(evidence="Thumbnail Validation Failure Detected", weight=0.5))
                score += 0.5
            elif node.node_type == TimelineNodeType.RECOVERY.value and "Succeeded" in node.title and "THUMBNAIL" in node.title:
                succeeded = True
                factors.append(ConfidenceFactor(evidence="Thumbnail Fallback Succeeded", weight=0.5))
                score += 0.5
                
        if has_failure:
            return RuleEvaluationResult(
                is_match=True,
                root_cause="External Asset Download Failure",
                confidence_score=min(1.0, round(score, 2)),
                factors=factors,
                status="AUTO_RESOLVED" if succeeded else "OPEN"
            )
            
        return RuleEvaluationResult(is_match=False)

class RedisTimeoutRule(BaseRootCauseRule):
    def evaluate(self, nodes: List[TimelineNode]) -> RuleEvaluationResult:
        factors = []
        score = 0.0
        has_redis_timeout = False
        
        for node in nodes:
            if node.node_type == TimelineNodeType.HEALTH_CHECK.value and "redis" in str(node.description).lower():
                has_redis_timeout = True
                factors.append(ConfidenceFactor(evidence="Redis Connection Timeout", weight=0.9))
                score += 0.9
                
        if has_redis_timeout:
            return RuleEvaluationResult(
                is_match=True,
                root_cause="Redis Timeout",
                confidence_score=min(1.0, round(score, 2)),
                factors=factors,
                status="MANUAL_REQUIRED"
            )
        return RuleEvaluationResult(is_match=False)

class QueueSaturationRule(BaseRootCauseRule):
    def evaluate(self, nodes: List[TimelineNode]) -> RuleEvaluationResult:
        factors = []
        score = 0.0
        has_saturation = False
        
        for node in nodes:
            if node.node_type == TimelineNodeType.HEALTH_CHECK.value and "queue depth" in str(node.description).lower():
                has_saturation = True
                factors.append(ConfidenceFactor(evidence="Queue Depth Extremely High", weight=0.9))
                score += 0.9
                
        if has_saturation:
            return RuleEvaluationResult(
                is_match=True,
                root_cause="Queue Saturation",
                confidence_score=min(1.0, round(score, 2)),
                factors=factors,
                status="MANUAL_REQUIRED"
            )
        return RuleEvaluationResult(is_match=False)
