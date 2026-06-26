from typing import Any


class ReflectionPolicy:
    """
    Base interface for post-generation reflection loops.
    """
    @property
    def policy_name(self) -> str:
        raise NotImplementedError

    async def reflect(self, context: Any, response: Any) -> Any:
        raise NotImplementedError

class NoReflection(ReflectionPolicy):
    @property
    def policy_name(self) -> str:
        return "NoReflection"

    async def reflect(self, context: Any, response: Any) -> Any:
        return response

class SelfCritiqueReflection(ReflectionPolicy):
    @property
    def policy_name(self) -> str:
        return "SelfCritique"

    async def reflect(self, context: Any, response: Any) -> Any:
        # Stub: LLM would evaluate its own response and potentially trigger a re-plan
        return response

class RecoveryStrategy:
    """
    Base interface for resolving pipeline/agent exceptions.
    """
    @property
    def strategy_name(self) -> str:
        raise NotImplementedError

    async def recover(self, exception: Exception, context: Any) -> Any:
        raise NotImplementedError

class FallbackModelStrategy(RecoveryStrategy):
    @property
    def strategy_name(self) -> str:
        return "FallbackModelStrategy"

    async def recover(self, exception: Exception, context: Any) -> Any:
        # Stub: Would switch profile to "Fast" or different provider and retry
        raise NotImplementedError("Fallback not implemented yet")

class AbortStrategy(RecoveryStrategy):
    @property
    def strategy_name(self) -> str:
        return "AbortStrategy"

    async def recover(self, exception: Exception, context: Any) -> Any:
        raise exception
