import requests
import httpx
import trafilatura
import newspaper
from bs4 import BeautifulSoup
from readability import Document
import tqdm
from dataclasses import dataclass
import hn
import time
import datetime
from html_generator import HTMLGenerator

import asyncio
import os
import aiofiles
import random as rnd
import ebooklib.epub as epub
from concat_htmls import html_files_to_pdf

URL_ENDPOINT = "https://hn.algolia.com/api/v1"
generator = HTMLGenerator(max_depth=3, max_comments_per_level=[5, 3, 3])


@dataclass
class Item:

    title: str
    hn_url: str  # url of hacker news post
    ori_url: str  # url of original source
    content: str
    kids: list[str]
    timestamp: int
    score: int

    # def __init__(self, title: str, url: str, content: str = None):
    #     self.title = title
    #     self.url = url
    #     self.content = content
    #     self.comments = []

    # def add_comment(self, comment: str):
    #     self.comments.append(comment)


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
    return hits


async def get_story(hit_result: dict):
    get_story_url = f"{URL_ENDPOINT}/items/"
    await asyncio.sleep(rnd.random())
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
    for story in tqdm.tqdm(stories):
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

    # 必须先添加导航组件（EPUB 标准要求）
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # 添加 HTML 内容
    spine = ["nav"]  # spine 必须以 nav 开头
    toc = []

    for i, html_text in tqdm.tqdm(enumerate(html_texts)):
        title = f"Story #{i+1}"
        file_name = f"story_{i:03d}.xhtml"
        item_id = f"story_{i}"

        item = epub.EpubHtml(title=title, file_name=file_name, uid=item_id, lang="en")
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
    output_filename = f"HackerNews_{datetime.datetime.now().strftime('%Y%m%d')}.epub"
    try:
        epub.write_epub(output_filename, book)
        print(f"EPUB 生成成功: {output_filename}")
        return output_filename
    except Exception as e:
        print(f"EPUB 生成失败: {str(e)}")
        raise


# def construct_epub_book(html_texts: list[str, str]):
#     book = epub.EpubBook()
#     book.set_title(f"Hacker News - {datetime.datetime.now().strftime('%Y-%m-%d')}")
#     book.add_author("SnowFox4004")

#     # toc = []
#     for i, html_text in enumerate(html_texts):
#         item = epub.EpubHtml(title=f"story_{i:03d}", file_name=f"{i}.xhtml", lang="en")
#         item.content = html_text
#         book.add_item(item)
#         # toc.append(book.get_item_with_id(f"{id}.xhtml"))
#     # 获取所有HTML项
#     html_items = [item for item in book.get_items() if isinstance(item, epub.EpubHtml)]

#     # # 创建目录 - 简单列表形式
#     # book.toc = [epub.Link(item.file_name, item.title, item.id) for item in html_items]

#     # 或更结构化的形式（推荐）
#     book.toc = [
#         epub.Section("Hacker News Stories"),
#         [epub.Link(item.file_name, item.title, item.id) for item in html_items],
#     ]

#     # book.toc = (
#     #     epub.EpubToc("Table of Contents"),
#     #     [item for item in book.get_items() if isinstance(item, epub.EpubHtml)],
#     # )
#     # book.add_item(epub.EpubNcx())
#     # book.add_item(epub.EpubNav())
#     # book.spine = ["nav"] + [
#     #     item for item in book.get_items() if isinstance(item, epub.EpubHtml)
#     # ]

#     epub.write_epub(
#         "HackerNews_{}.epub".format(datetime.datetime.now().strftime("%Y%m%d")), book
#     )


async def get_original_page(target_dir: str, url: str, id: str, save_flag: bool):
    result = f"<h1> ERROR </h1><br><a href={url}>{url}</a>"
    err_flag = False
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url)
            response.raise_for_status()

            blog_content = response.content.decode(response.encoding)
            result = trafilatura.extract(
                blog_content, output_format="html", include_formatting=True
            )

            if result is None:
                result = f"<h1> ERROR </h1><br><a href={url}>{url}</a>"
    except:
        err_flag = True

    if save_flag:
        async with aiofiles.open(
            os.path.join(target_dir, f"{id}_ori.html"), "w+", encoding="utf-8"
        ) as fp:
            await fp.write(result)

    print(f"get original {url[8:50]:>45} done. error?: {err_flag}")
    return result


# def get_hn_top_stories():
#     url = "https://hacker-news.firebaseio.com/v0/topstories.json"
#     response = requests.get(url)
#     response = response.json()

#     fetched_stories = []

#     for story_id in tqdm.tqdm(response[:10], desc="Fetching stories"):
#         story = requests.get(
#             f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
#         )
#         story = story.json()
#         new_story = Story(story["title"], story["url"])
#         print(story)

#         fetched_stories.append(new_story)
#         for comment in story["kids"][:5]:
#             comment = requests.get(
#                 f"https://hacker-news.firebaseio.com/v0/item/{comment}.json"
#             )
#             comment = comment.json()
#             print(comment)

#             new_story.add_comment(f'{comment.get("by")}: {comment.get("text")}')

#     return fetched_stories


if __name__ == "__main__":
    # stories = get_hn_top_stories()
    # for story in stories:
    #     print(story.title)
    #     print(story.url)
    #     print(story.content)
    #     print("\n\t", end="")
    #     print(*story.comments, sep="\n\t")
    #     print()

    # weekly = asyncio.run(search_weekly_top_stories(20))
    # print(len(weekly))
    # downloaded = asyncio.run(download_stories(weekly, save_to_file=True))
    # print(len(downloaded))
    # # construct_epub_book(downloaded)

    current_date = datetime.datetime.now().date()
    target_path = "stories/" + f"{current_date.year}-{current_date.month}/"
    html_files_to_pdf(
        [os.path.join(target_path, i) for i in os.listdir(target_path)],
        "output.pdf",
        paper_size="A5",
    )
