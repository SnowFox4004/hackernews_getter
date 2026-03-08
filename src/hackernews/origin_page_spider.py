"""Origin page spider - entry point for fetching original content.

This module provides a registry-based dispatcher for fetching content
from different domains. Domain-specific handlers are registered in
the handlers/ subdirectory.
"""

from __future__ import annotations

import asyncio

from handlers import get_handler, list_registered_domains


def get_pathable_text(text: str) -> str:
    """Convert text to a safe filename string.

    Args:
        text: Input text to sanitize

    Returns:
        Sanitized string safe for use as filename
    """
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    text = text.replace("\t", " ")
    text = text.replace("?", " ")
    text = text.replace("/", " ")
    text = text.replace("\\", " ")
    text = text.replace("*", " ")
    text = text.replace('"', " ")
    text = text.replace("<", " ")
    text = text.replace(">", " ")
    text = text.replace("|", " ")
    text = text.replace(":", " ")
    text = text.replace(";", " ")
    text = text.replace("'", " ")
    text = text.replace("&", " ")
    return text[:50].strip()


async def get_origin(url: str, headers: dict) -> tuple[str, bool]:
    """Fetch original page content using domain-specific handler.

    This function dispatches to the appropriate handler based on the URL's domain.
    If no specific handler is registered for the domain, the default handler is used.

    Args:
        url: Target URL to fetch
        headers: HTTP request headers

    Returns:
        Tuple of (content, is_error)
        - content: str - Extracted HTML content
        - is_error: bool - True if extraction failed
    """
    handler = get_handler(url)
    return await handler(url, headers)


if __name__ == "__main__":
    # Test/demo code
    print("Registered domains:", list_registered_domains())

    url = "https://x.com/Muffinisme/status/2023080167804137713"
    blog_content = asyncio.run(
        get_origin(
            url,
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            },
        )
    )
    open("./outs/test.html", "w", encoding="utf-8").write(blog_content[0])
    print(f"Content length: {len(blog_content[0])}")
    print(f"Is error: {blog_content[1]}")
