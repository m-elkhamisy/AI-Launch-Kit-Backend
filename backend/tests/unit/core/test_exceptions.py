from launchkit.core.exceptions import (
    ApplicationError,
    ConfigurationError,
    DomainError,
    LaunchKitError,
)


def test_exception_hierarchy() -> None:
    assert issubclass(DomainError, LaunchKitError)
    assert issubclass(ApplicationError, LaunchKitError)
    assert issubclass(ConfigurationError, ApplicationError)
