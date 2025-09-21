import asyncio
import datetime
import html
import os
import random as rnd
import time

import aiofiles
import ebooklib.epub as epub
import httpx
import tqdm
import trafilatura

from concat_htmls import html_files_to_pdf
from html_generator import HTMLGenerator

URL_ENDPOINT = "https://hn.algolia.com/api/v1"
generator = HTMLGenerator(max_depth=3, max_comments_per_level=[5, 3, 3])

HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,zh-TW;q=0.5",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "priority": "u=0, i",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
}

async def get_time_range():
    # timestamp of 1 week ago and now
    now = int(time.time())
    one_week_ago = now - 60 * 60 * 24 * 7
    return one_week_ago, now


async def search_weekly_top_stories(num_stories: int):
    SEARCH_ENDPOINT = "/search"
    search_url = URL_ENDPOINT + SEARCH_ENDPOINT

    hits = []
    page = 1
    async with httpx.AsyncClient() as client:
        while len(hits) < num_stories:
            start_time, end_time = await get_time_range()
            params = {
                "tags": "story",
                "numericFilters": f"created_at_i>{start_time},created_at_i<{end_time}",
                "page": page,
            }
            response = await client.get(search_url, params=params)

            print(
                f"Fetched {response.url} - {response.status_code}: {response.text if len(response.text) < 1000 else 'maybe normal'}"
            )

            hits += response.json()["hits"]
            page += 1
    return hits[:num_stories]


async def get_story(hit_result: dict):
    get_story_url = f"{URL_ENDPOINT}/items/"
    await asyncio.sleep(rnd.random() * 1.5)
    async with httpx.AsyncClient(timeout=25) as client:
        story_id = hit_result["objectID"]
        story_url = get_story_url + story_id
        story = await client.get(story_url)
        story = story.json()
        print(f"get story {story_id} done.")
        return story


async def download_stories(hits: list, save_to_file: bool = False):
    current_date = datetime.datetime.now().date()
    html_texts = []

    target_dir = "stories/" + f"{current_date.year}-{current_date.month}/"
    os.makedirs(target_dir, exist_ok=True)

    tasks = [
        asyncio.create_task(get_story(hit))
        for hit in hits
        # if not os.path.exists(os.path.join(target_dir, f"{hit['objectID']}.html"))
    ]
    stories = await asyncio.gather(*tasks)
    story_texts = []
    for story in tqdm.tqdm(stories, total=len(stories)):
        if save_to_file:
            generator.save_html(story, os.path.join(target_dir, f"{story['id']}.html"))

        html_text = generator.generate_html(story)
        story_texts.append(html_text)

    origin_page_tasks = [
        asyncio.create_task(
            get_original_page(target_dir, hit["url"], hit["id"], save_to_file)
        )
        for hit in stories
    ]
    origin_pages = await asyncio.gather(*origin_page_tasks)

    for hn, ori in zip(story_texts, origin_pages):
        html_texts.append(ori)
        html_texts.append(hn)

    return html_texts


def construct_epub_book(html_texts: list[str]):
    """
    构建包含 Hacker News 故事的 EPUB 电子书

    Args:
        html_texts: 包含 HTML 内容的字符串列表
    """
    book = epub.EpubBook()
    book.set_title(f"Hacker News - {datetime.datetime.now().strftime('%Y-%m-%d')}")
    book.add_author("SnowFox4004")

    # 必须先添加导航组件
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    spine = ["nav"]
    toc = []

    # 创建CSS样式文件
    css_content = """
    body {
        font-family: Georgia, serif;
        font-size: 12pt;
        line-height: 1.4;
        margin: 20px;
        color: #000000;
    }
    h1 {
        font-size: 18pt;
    }
    .story-info {
        font-size: 10pt;
        color: #666666;
        margin: 10px 0;
    }
    .comment {
        border-left: 1px solid #cccccc;
        margin: 10px 0;
        padding-left: 10px;
    }
    .comment-header {
        font-size: 10pt;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .comment-text {
        margin: 5px 0;
    }
    .comment-level-0 { margin-left: 0; }
    .comment-level-1 { margin-left: 20px; }
    .comment-level-2 { margin-left: 40px; }
    .comment-level-3 { margin-left: 60px; }
    .comment-level-4 { margin-left: 80px; }
    .comment-level-5 { margin-left: 100px; }
    """

    # 创建EPUB CSS项目
    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name="style/nav.css",
        media_type="text/css",
        content=css_content,
    )

    # 添加CSS到书籍
    book.add_item(nav_css)

    for i, html_text in tqdm.tqdm(enumerate(html_texts), total=len(html_texts)):
        title = f"Story #{i+1}"
        file_name = f"story_{i:03d}.xhtml"
        item_id = f"story_{i}"

        item = epub.EpubHtml(title=title, file_name=file_name, uid=item_id, lang="en")

        html_text = html.unescape(html_text)
        if "<style>" in html_text:
            # 样式放在body内才会在epub.write_epub()中保留

            html_text = html_text.replace(
                "<body>",
                f"<body><style>{css_content}</style>",
                1,
            )

        # if i == 1:
        #     print(html_text)

        item.content = html_text
        book.add_item(item)

        # 添加到 spine 和目录
        spine.append(item)
        toc.append(epub.Link(file_name, title, item_id))

    # 修复关键点：正确设置 TOC 结构
    book.toc = [(epub.Section("Hacker News Weekly Digest"), toc)]

    # 设置 spine（内容阅读顺序）
    book.spine = spine

    # 生成 EPUB 文件
    output_filename = "outs/" + f"HackerNews.epub"
    try:
        epub.write_epub(output_filename, book)
        print(f"EPUB 生成成功: {output_filename}")
        return output_filename
    except Exception as e:
        print(f"EPUB 生成失败: {str(e)}")
        raise


async def get_original_page(target_dir: str, url: str, id: str, save_flag: bool):
    result = f"<h1> ERROR </h1><br><a href={url}>{url}</a>"
    err_flag = False
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, headers=HEADERS, follow_redirects=True)
            response.raise_for_status()

            try:
                blog_content = response.content.decode(response.encoding)
            except:
                blog_content = response.text

            result = trafilatura.extract(
                blog_content,
                output_format="html",
                include_formatting=True,
                favor_recall=True,
            )

            if result is None:
                result = f"<h1> ERROR </h1><br><a href={url}>{url}</a>"
    except Exception as err:
        err_flag = True
        result = f"<h1> ERROR </h1><br><a href={url}>{url}</a><br><p>{str(err)}</p>"

    if save_flag:
        async with aiofiles.open(
            os.path.join(target_dir, f"{id}_ori.html"), "w+", encoding="utf-8"
        ) as fp:
            await fp.write(result)

    print(f"get original {url[8:50]:>45} done. error?: {err_flag}")
    return result

if __name__ == "__main__":
    os.makedirs("outs/", exist_ok=True)

    weekly = asyncio.run(search_weekly_top_stories(25))
    print("get", len(weekly), "top stories.")
    downloaded = asyncio.run(download_stories(weekly, save_to_file=True))
    print("downloaded", len(downloaded), "stories.")

    construct_epub_book(downloaded)

    current_date = datetime.datetime.now().date()
    target_path = "stories/" + f"{current_date.year}-{current_date.month}/"
    html_files_to_pdf(
        [os.path.join(target_path, i) for i in os.listdir(target_path)],
        "outs/output.pdf",
        paper_size="A5",
    )
