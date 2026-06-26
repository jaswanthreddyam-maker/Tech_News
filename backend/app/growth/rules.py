import hashlib
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, ClassVar

from app.growth.schemas import FeatureFlagContext


class GrowthRule(ABC):
    """
    Capability interface for growth platform rules (Feature Flags, Experiments, etc).
    """
    @property
    @abstractmethod
    def rule_type(self) -> str:
        pass

    @abstractmethod
    def evaluate(self, context: FeatureFlagContext, config: dict[str, Any], flag_key: str, rule_version: str = "1.0") -> Any | None:
        """
        Evaluates the rule against the context.
        Returns the mapped value if it matches, otherwise None.
        """
        pass


class EmergencyRule(GrowthRule):
    """
    Emergency kill-switch rule. High priority.
    Config expects: {"active": bool, "value": Any}
    """
    @property
    def rule_type(self) -> str:
        return "EmergencyRule"

    def evaluate(self, context: FeatureFlagContext, config: dict[str, Any], flag_key: str, rule_version: str = "1.0") -> Any | None:
        if config.get("active") is True:
            return config.get("value")
        return None


class PercentageRule(GrowthRule):
    """
    Deterministically rolls out a feature to a percentage of users.
    Config expects: {"percentage": int, "value": Any}
    """
    @property
    def rule_type(self) -> str:
        return "PercentageRule"

    def evaluate(self, context: FeatureFlagContext, config: dict[str, Any], flag_key: str, rule_version: str = "1.0") -> Any | None:
        if not context.user_id:
            # Cannot do deterministic percentage rollout without an identifier
            # Fall back to session_id if user_id is absent
            identifier = context.session_id
            if not identifier:
                return None
        else:
            identifier = context.user_id

        percentage = config.get("percentage", 0)
        value = config.get("value")

        # Support versioned algorithms. Right now v1 is md5, v2 could be xxhash.
        if rule_version == "1.0" or rule_version == "v1":
            hash_input = f"{identifier}_{flag_key}".encode()
            hash_val = int(hashlib.md5(hash_input).hexdigest()[:8], 16)
            bucket = hash_val % 100
        else:
            # Default fallback algorithm for demo purposes
            hash_input = f"{identifier}_{flag_key}".encode()
            hash_val = int(hashlib.md5(hash_input).hexdigest()[:8], 16)
            bucket = hash_val % 100

        if bucket < percentage:
            return value
        return None


class UserRule(GrowthRule):
    """
    Targets specific user IDs.
    Config expects: {"user_ids": list[str], "value": Any}
    """
    @property
    def rule_type(self) -> str:
        return "UserRule"

    def evaluate(self, context: FeatureFlagContext, config: dict[str, Any], flag_key: str, rule_version: str = "1.0") -> Any | None:
        if not context.user_id:
            return None

        allowed_users = config.get("user_ids", [])
        if context.user_id in allowed_users:
            return config.get("value")
        return None


class CountryRule(GrowthRule):
    """
    Targets specific countries.
    Config expects: {"countries": list[str], "value": Any}
    """
    @property
    def rule_type(self) -> str:
        return "CountryRule"

    def evaluate(self, context: FeatureFlagContext, config: dict[str, Any], flag_key: str, rule_version: str = "1.0") -> Any | None:
        if not context.country:
            return None

        allowed_countries = config.get("countries", [])
        # case-insensitive check
        if context.country.upper() in [c.upper() for c in allowed_countries]:
            return config.get("value")
        return None


class AppVersionRule(GrowthRule):
    """
    Targets specific application versions (e.g., iOS > 1.2.0).
    Config expects: {"versions": list[str], "value": Any}
    """
    @property
    def rule_type(self) -> str:
        return "AppVersionRule"

    def evaluate(self, context: FeatureFlagContext, config: dict[str, Any], flag_key: str, rule_version: str = "1.0") -> Any | None:
        if not context.app_version:
            return None

        allowed_versions = config.get("versions", [])
        if context.app_version in allowed_versions:
            return config.get("value")
        return None


class TimeWindowRule(GrowthRule):
    """
    Evaluates to a value only within a specific UTC time window.
    Config expects: {"start_time": str (ISO 8601), "end_time": str (ISO 8601), "value": Any}
    """
    @property
    def rule_type(self) -> str:
        return "TimeWindowRule"

    def evaluate(self, context: FeatureFlagContext, config: dict[str, Any], flag_key: str, rule_version: str = "1.0") -> Any | None:
        try:
            start_time_str = config.get("start_time")
            end_time_str = config.get("end_time")

            current_time = context.timestamp

            if start_time_str:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                # Ensure context timestamp is timezone aware if comparing to aware objects
                if current_time.tzinfo is None and start_time.tzinfo is not None:
                    # simplistic assumption UTC if naive
                    from datetime import timezone
                    current_time = current_time.replace(tzinfo=timezone.utc)

                if current_time < start_time:
                    return None

            if end_time_str:
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                if current_time.tzinfo is None and end_time.tzinfo is not None:
                    from datetime import timezone
                    current_time = current_time.replace(tzinfo=timezone.utc)

                if current_time > end_time:
                    return None

            return config.get("value")
        except Exception:
            return None


class RuleRegistry:
    """
    Registry for resolving GrowthRule capabilities.
    """
    _rules: ClassVar[dict[str, GrowthRule]] = {}

    @classmethod
    def register(cls, rule: GrowthRule):
        cls._rules[rule.rule_type] = rule

    @classmethod
    def get_rule(cls, rule_type: str) -> GrowthRule | None:
        return cls._rules.get(rule_type)

    @classmethod
    def evaluate(cls, rule_type: str, context: FeatureFlagContext, config: dict[str, Any], flag_key: str, rule_version: str = "1.0") -> Any | None:
        rule = cls.get_rule(rule_type)
        if rule:
            return rule.evaluate(context, config, flag_key, rule_version)
        return None


# Bootstrap rules
RuleRegistry.register(EmergencyRule())
RuleRegistry.register(PercentageRule())
RuleRegistry.register(UserRule())
RuleRegistry.register(CountryRule())
RuleRegistry.register(AppVersionRule())
RuleRegistry.register(TimeWindowRule())
