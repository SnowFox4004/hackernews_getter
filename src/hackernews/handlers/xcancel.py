"""Handler for x.com and twitter.com domains.

This handler redirects requests to xcancel.com (a Twitter/X proxy)
to avoid rate limiting and access restrictions.
"""

from __future__ import annotations

import re

from handlers import register_handler
from handlers.default import default_handler


@register_handler("x.com")
@register_handler("twitter.com")
async def xcancel_handler(url: str, headers: dict) -> tuple[str, bool]:
    """Handle x.com and twitter.com URLs by redirecting to xcancel.com.

    Uses non-headless browser mode to bypass human verification challenges.

    Args:
        url: Target URL (x.com or twitter.com)
        headers: HTTP request headers

    Returns:
        Tuple of (content, is_error)
    """
    # Replace domain: x.com -> xcancel.com, twitter.com -> xcancel.com
    new_url = re.sub(
        r'^(https?://)(?:x|twitter)\.com',
        r'\1xcancel.com',
        url
    )

    print(f"Redirecting: {url} -> {new_url}")
    print("Using non-headless mode for x.com/twitter.com to bypass verification")

    # Use non-headless mode to bypass human verification
    return await default_handler(new_url, headers, headless=False)
