from __future__ import annotations
import logging

logger = logging.getLogger("app.sentry")

_sentry_initialized = False


def init_sentry(dsn: str | None = None) -> bool:
    """
    Initialize Sentry if DSN is provided.

    Args:
        dsn: Sentry DSN from environment or settings

    Returns:
        True if Sentry was initialized, False otherwise
    """
    global _sentry_initialized

    if not dsn:
        logger.info("Sentry DSN not provided, skipping initialization")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.asgi import AsgiIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[
                AsgiIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
            ],
            traces_sample_rate=0.1,
            environment="development" if dsn.startswith("http://localhost") else "production",
        )

        _sentry_initialized = True
        logger.info("Sentry initialized successfully")
        return True

    except ImportError:
        logger.warning("sentry-sdk not installed, skipping Sentry initialization")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def is_sentry_initialized() -> bool:
    """Check if Sentry was successfully initialized."""
    return _sentry_initialized