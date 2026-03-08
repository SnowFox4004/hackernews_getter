"""Origin page handlers registry.

This module provides a registry pattern for handling different domains
with specialized content extraction logic.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from urllib.parse import urlparse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Type alias for origin page handlers
OriginHandler = Callable[[str, dict], Awaitable[tuple[str, bool]]]

# Registry: domain -> handler function
_ORIGIN_HANDLERS: dict[str, OriginHandler] = {}

# Default handler will be set after importing default module
_default_handler: OriginHandler | None = None


def register_handler(domain: str) -> Callable[[OriginHandler], OriginHandler]:
    """Decorator to register a handler for a specific domain.

    Args:
        domain: The domain to match (e.g., "x.com", "twitter.com")

    Returns:
        Decorator function

    Example:
        @register_handler("x.com")
        async def x_handler(url: str, headers: dict) -> tuple[str, bool]:
            ...
    """
    def decorator(func: OriginHandler) -> OriginHandler:
        _ORIGIN_HANDLERS[domain] = func
        return func
    return decorator


def set_default_handler(handler: OriginHandler) -> None:
    """Set the default handler for unmatched domains."""
    global _default_handler
    _default_handler = handler


def get_handler(url: str) -> OriginHandler:
    """Get the appropriate handler for a URL.

    Args:
        url: The target URL to fetch

    Returns:
        Handler function for the domain, or default handler if not found
    """
    parsed = urlparse(url)
    domain = parsed.netloc

    handler = _ORIGIN_HANDLERS.get(domain)
    if handler is not None:
        return handler

    # Fallback to default handler
    if _default_handler is None:
        raise RuntimeError("Default handler not set. Import handlers.default first.")
    return _default_handler


def list_registered_domains() -> list[str]:
    """List all registered domains."""
    return list(_ORIGIN_HANDLERS.keys())


# Import handlers to register them
from handlers import default, xcancel

__all__ = [
    "OriginHandler",
    "register_handler",
    "set_default_handler",
    "get_handler",
    "list_registered_domains",
    "default",
    "xcancel",
]
