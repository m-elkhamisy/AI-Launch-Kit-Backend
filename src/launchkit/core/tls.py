"""Use operating-system trust stores for outbound TLS (corporate proxies re-sign certs)."""

import structlog


def use_system_certificates() -> None:
    """Make ssl.SSLContext chain to the OS store so proxy CAs are trusted."""

    try:
        import truststore
    except ImportError:
        structlog.get_logger(__name__).warning("truststore_not_installed")
        return
    truststore.inject_into_ssl()
