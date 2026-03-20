"""Custom exception hierarchy for NEXUS."""


class NexusError(Exception):
    """Base exception for all NEXUS errors."""
    pass


class GeminiError(NexusError):
    """Raised when Gemini API calls fail."""
    pass


class ValidationError(NexusError):
    """Raised when input validation fails."""
    pass


class StorageError(NexusError):
    """Raised when Google Cloud Storage operations fail."""
    pass


class RateLimitError(NexusError):
    """Raised when a client exceeds the allowed rate limit."""
    pass


class APIError(NexusError):
    """Raised when an external API fails."""
    pass


class DatabaseError(NexusError):
    """Raised when a database operation fails."""
    pass
