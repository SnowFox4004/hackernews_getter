from playwright.async_api import async_playwright
import asyncio


async def get_page_content(url: str):
    async with async_playwright() as pw:
        browser = await pw.firefox.launch(headless=True)
        page = await browser.new_page()

        # 伪装成真实浏览器
        await page.add_init_script(
            """
            navigator.webdriver = undefined;
            navigator.plugins.length = 1;
            navigator.platform = 'Win32';
        """
        )

        # 设置用户代理
        await page.set_extra_http_headers(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as err:
            content = "Time limite exceeded in playwright"
            return content

        content = await page.content()
        await browser.close()
        return content
    return "unknown error"


if __name__ == "__main__":
    url = "https://hackerone.com/reports/3340109"
    blog_content = asyncio.run(get_page_content(url))
    # print(content)

    import trafilatura

    content = trafilatura.extract(
        blog_content,
        output_format="txt",
        include_formatting=True,
        favor_recall=True,
        include_images=True,
    )
    print(content)
