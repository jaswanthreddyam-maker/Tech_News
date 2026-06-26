from app.services.recovery.models import RecoveryDecision

class BaseRecoveryPolicy:
    def __init__(self, recovery_type: str, cooldown_minutes: int):
        self.recovery_type = recovery_type
        self.cooldown_minutes = cooldown_minutes

    async def evaluate(self, metrics: dict, redis_state: dict) -> RecoveryDecision:
        raise NotImplementedError

class CQRSRecoveryPolicy(BaseRecoveryPolicy):
    def __init__(self):
        super().__init__(recovery_type="cqrs", cooldown_minutes=15)

    async def evaluate(self, metrics: dict, redis_state: dict) -> RecoveryDecision:
        projection_lag = metrics.get("projection_lag", 0)
        cooldown = redis_state.get("cooldown_remaining", 0)
        failures = redis_state.get("consecutive_failures", 0)

        if projection_lag > 10:
            if cooldown > 0:
                return RecoveryDecision(
                    approved=False,
                    reason=f"Projection lag high ({projection_lag}), but recovery is on cooldown.",
                    recovery_type=self.recovery_type,
                    cooldown_remaining=cooldown,
                    consecutive_failures=failures
                )
            return RecoveryDecision(
                approved=True,
                reason=f"Projection lag critically high ({projection_lag}). Initiating failed batch replay.",
                recovery_type=self.recovery_type,
                cooldown_remaining=0,
                consecutive_failures=failures
            )
            
        return RecoveryDecision(
            approved=False,
            reason="CQRS is healthy.",
            recovery_type=self.recovery_type,
            cooldown_remaining=cooldown,
            consecutive_failures=failures
        )

class ThumbnailRecoveryPolicy(BaseRecoveryPolicy):
    def __init__(self):
        super().__init__(recovery_type="thumbnail", cooldown_minutes=30)

    async def evaluate(self, metrics: dict, redis_state: dict) -> RecoveryDecision:
        failure_rate = metrics.get("missing_rate", 0.0)
        cooldown = redis_state.get("cooldown_remaining", 0)
        failures = redis_state.get("consecutive_failures", 0)

        if failure_rate > 10.0:
            if cooldown > 0:
                return RecoveryDecision(
                    approved=False,
                    reason=f"Thumbnail failure rate high ({failure_rate}%), but recovery is on cooldown.",
                    recovery_type=self.recovery_type,
                    cooldown_remaining=cooldown,
                    consecutive_failures=failures
                )
            return RecoveryDecision(
                approved=True,
                reason=f"Thumbnail failure rate critically high ({failure_rate}%). Initiating thumbnail recovery.",
                recovery_type=self.recovery_type,
                cooldown_remaining=0,
                consecutive_failures=failures
            )
            
        return RecoveryDecision(
            approved=False,
            reason="Thumbnails are healthy.",
            recovery_type=self.recovery_type,
            cooldown_remaining=cooldown,
            consecutive_failures=failures
        )

class QueueRecoveryPolicy(BaseRecoveryPolicy):
    def __init__(self):
        super().__init__(recovery_type="queue", cooldown_minutes=15)

    async def evaluate(self, metrics: dict, redis_state: dict) -> RecoveryDecision:
        # Currently in recommendation mode only
        total_depth = metrics.get("rss_queue_depth", 0) + metrics.get("projection_queue_depth", 0) + metrics.get("thumbnail_queue_depth", 0)
        cooldown = redis_state.get("cooldown_remaining", 0)
        failures = redis_state.get("consecutive_failures", 0)

        if total_depth > 200:
            return RecoveryDecision(
                approved=False,
                reason=f"Queue depth extremely high ({total_depth}). Recommendation: Restart consumers or replay stalled work. Automation disabled for queues.",
                recovery_type=self.recovery_type,
                cooldown_remaining=cooldown,
                consecutive_failures=failures
            )

        return RecoveryDecision(
            approved=False,
            reason="Queues are healthy.",
            recovery_type=self.recovery_type,
            cooldown_remaining=cooldown,
            consecutive_failures=failures
        )
