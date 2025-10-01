from playwright.async_api import async_playwright
import asyncio
import httpx
import bs4 as BeautifulSoup
import trafilatura

async def get_page_content_playwright(url: str):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()

        # 伪装成真实浏览器
        # await page.set_viewport_size(1920, 1080)

        # 设置用户代理
        await page.set_extra_http_headers(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(5)
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
    return "unknown error"


async def get_page_content_requests(url: str, headers: dict):
    async with httpx.AsyncClient(
        timeout=30.0, verify=False, follow_redirects=True
    ) as client:
        try:
            response = await client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()
        except Exception as err:
            # print(f"Error fetching {url}: {err}")
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


async def concat_htmls(html_list: list[str]):
    htmls = [
        (html[0], BeautifulSoup.BeautifulSoup(html[1], "html.parser"))
        for html in html_list
    ]
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
            # print(f"html has no body tag, appending whole html ")
            for element in html.children:
                concated.body.append(element.extract())

    return str(concated)


def get_pathable_text(text: str):
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


async def get_origin(url: str, headers: dict):
    is_error = False
    try:
        content = await get_page_content_requests(url, headers)

        text_len = BeautifulSoup.BeautifulSoup(content, "html.parser").text
        # print(f"text length of {url} is {len(text_len)}")
        if content is None or len(text_len) < 500:
            print(
                f"simple request result of {str(url)[8:50]:>45} seems bad. trying to use playwright..."
            )
            pw_content = await get_page_content_playwright(url)
            content = await concat_htmls(
                [("request", content), ("playwright", pw_content)]
            )

            open(
                f"./stories/pw_res_{get_pathable_text(url)}.html",
                "w+",
                encoding="utf-8",
            ).write(content)
            text_len = BeautifulSoup.BeautifulSoup(content, "html.parser").text
            if content is None or len(text_len) < 500:
                is_error = True
    except Exception as e:
        print(f"Error processing {str(url)[8:50]:>45}: {e}")
        # raise e
        is_error = True
        content = f"<h1> ERROR </h1><br><a href={url}>{url}</a><p> get origin Exception occurred: {e}</p>"

    return content, is_error


if __name__ == "__main__":
    url = "https://www.nbcnews.com/news/us-news/death-rates-rose-hospital-ers-private-equity-firms-took-study-finds-rcna233211"
    blog_content = asyncio.run(
        get_origin(
            url,
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            },
        )
    )
    # print(content)

    # import trafilatura

    content = trafilatura.extract(
        blog_content,
        output_format="txt",
        include_formatting=True,
        favor_recall=True,
        include_images=True,
    )
    print(content)
