"""Shared exception hierarchy independent of HTTP transports."""


class LaunchKitError(Exception):
    """Base class for expected backend failures."""


class DomainError(LaunchKitError):
    """Raised when domain input or state violates a business rule."""


class ApplicationError(LaunchKitError):
    """Raised when an application capability cannot complete."""


class ConfigurationError(ApplicationError):
    """Raised when required runtime configuration is invalid or missing."""
