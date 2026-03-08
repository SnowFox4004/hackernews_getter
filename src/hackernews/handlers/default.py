"""Default origin page handler using trafilatura + playwright fallback.

This handler uses httpx + trafilatura as primary method,
and falls back to playwright for dynamic pages.
"""

from __future__ import annotations

import asyncio

import httpx
import trafilatura
from bs4 import BeautifulSoup
from patchright.async_api import async_playwright
from playwright_stealth import Stealth

from handlers import set_default_handler


async def get_page_content_playwright(url: str, headless: bool = True) -> str | None:
    """Fetch page content using Playwright browser.

    Args:
        url: Target URL
        headless: Whether to run browser in headless mode. Set to False for
                  sites that require human verification (e.g., x.com).

    Returns:
        Extracted HTML content or None on failure
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        page = await browser.new_page()

        await page.set_extra_http_headers(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(10)
            await page.wait_for_load_state("networkidle")
        except Exception as err:
            print("Time limit exceeded in playwright", f"{str(url)[8:50]:>45}")
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(5)
            return await page.content()

        content = await page.content()
        content = trafilatura.extract(
            content,
            output_format="html",
            include_formatting=True,
            favor_recall=True,
            include_images=True,
        )
        await browser.close()
        return content


async def get_page_content_requests(url: str, headers: dict) -> str:
    """Fetch page content using httpx requests.

    Args:
        url: Target URL
        headers: HTTP request headers

    Returns:
        Extracted HTML content or error message
    """
    async with httpx.AsyncClient(
        timeout=30.0, verify=False, follow_redirects=True
    ) as client:
        try:
            response = await client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()
        except Exception as err:
            return f"HTTPX Error: {err}"
        blog_content = response.text

        result = trafilatura.extract(
            blog_content,
            output_format="html",
            include_formatting=True,
            favor_recall=True,
            include_images=True,
        )

        if result is None:
            result = f"<html><body><h1> ERROR </h1><br><a href={url}>{url}</a><p> result is None.</p></body></html>"
        return result


async def concat_htmls(html_list: list[tuple[str, str]]) -> str:
    """Concatenate multiple HTML contents.

    Args:
        html_list: List of (title, html_content) tuples

    Returns:
        Merged HTML string
    """
    htmls = [(html[0], BeautifulSoup(html[1], "html.parser")) for html in html_list]
    idx = 0
    while idx < len(htmls) and not htmls[idx][1].body:
        idx += 1
    concated = htmls[idx][max(idx, len(htmls) - 1)]

    for method_id, (title, html) in enumerate(htmls):
        if method_id == idx:
            continue

        hr_tag = concated.new_tag("hr")
        heading = concated.new_tag("h2")
        heading.string = f"Content from method {title}"

        concated.body.append(hr_tag)
        concated.body.append(heading)

        if html.body:
            for element in html.body.children:
                concated.body.append(element.extract())
        else:
            for element in html.children:
                concated.body.append(element.extract())

    return str(concated)


async def default_handler(url: str, headers: dict, headless: bool = True) -> tuple[str, bool]:
    """Default handler for origin page extraction.

    Uses httpx + trafilatura first, falls back to playwright if content is too short.

    Args:
        url: Target URL to fetch
        headers: HTTP request headers
        headless: Whether to run browser in headless mode. Set to False for
                  sites that require human verification (e.g., x.com).

    Returns:
        Tuple of (content, is_error)
        - content: Extracted HTML content
        - is_error: True if extraction failed
    """
    is_error = False
    try:
        content = await get_page_content_requests(url, headers)

        text_len = BeautifulSoup(content, "html.parser").text
        if content is None or len(str(text_len)) < 500:
            print(
                f"simple request result of {str(url)[8:50]:>45} seems bad. trying to use playwright..."
            )
            pw_content = await get_page_content_playwright(url, headless=headless)
            content = await concat_htmls(
                [("request", content), ("playwright", pw_content)]
            )

            text_len = BeautifulSoup(content, "html.parser").text
            if content is None or len(text_len) < 500:
                is_error = True
    except Exception as e:
        print(f"Error processing {str(url)[8:50]:>45}: {e}")
        is_error = True
        content = f"<h1> ERROR </h1><br><a href={url}>{url}</a><p> get origin Exception occurred: {e}</p>"

    return content, is_error


# Register as default handler
set_default_handler(default_handler)
