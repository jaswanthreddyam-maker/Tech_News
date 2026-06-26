class AIError(Exception):
    """Base exception for AI infrastructure errors."""


class AIConfigurationError(AIError):
    """Raised when AI configuration is missing or invalid."""


class AIProviderNotConfigured(AIConfigurationError):
    """Raised when a selected provider has not been wired with credentials/client code."""


class AIProviderError(AIError):
    """Raised when a provider request fails."""


class AIProviderTimeout(AIProviderError):
    """Raised when a provider request times out."""


class AIResponseValidationError(AIError):
    """Raised when provider output cannot be validated as structured data."""


class AIPromptError(AIError):
    """Raised when a prompt template cannot be loaded."""


class AIBudgetExceeded(AIError):
    """Raised when a configured AI cost budget would be exceeded."""
