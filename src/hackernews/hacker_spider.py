import asyncio
import datetime
import html
import os
import random as rnd

import aiofiles
import ebooklib.epub as epub
import httpx
import tqdm

import origin_page_spider as originSpider
from concat_htmls import html_files_to_pdf
from html_generator import HTMLGenerator
from html_img_embedder import embed_images_in_html_string
from utils import get_time_range_last_week

URL_ENDPOINT = "https://hn.algolia.com/api/v1"
generator = HTMLGenerator(max_depth=3, max_comments_per_level=[5, 3, 3])

HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
}


async def search_stories_byTimeRange(
    num_stories: int,
    start_time: int,
    end_time: int,
    title: str = None,
):
    SEARCH_ENDPOINT = "/search"
    search_url = URL_ENDPOINT + SEARCH_ENDPOINT

    hits = []
    page = 0
    async with httpx.AsyncClient() as client:
        while len(hits) < num_stories:
            # start_time, end_time = await get_time_range_last_week()
            params = {
                "tags": "story",
                "numericFilters": f"created_at_i>{start_time},created_at_i<{end_time}",
                "page": page,
            }
            if title is not None and title:
                params["query"] = title
            response = await client.get(search_url, params=params)

            print(
                f"Fetched {response.url} - {response.status_code}: {response.text if len(response.text) < 1000 else 'maybe normal'}"
            )

            hits += response.json()["hits"]
            page += 1
    return hits[:num_stories]


async def get_story(hit_id: int):
    get_story_url = f"{URL_ENDPOINT}/items/"
    await asyncio.sleep(rnd.random() * 2)
    async with httpx.AsyncClient(timeout=25) as client:
        story_id = hit_id
        story_url = get_story_url + str(story_id)
        story = await client.get(story_url)
        story = story.json()
        print(f"get story {story.get("title", None) or story_id:>80} done.")
        return story


async def download_stories(
    hits: list, save_to_file: bool = False, output_dir: str = "stories/"
):
    """
    Download Hacker News stories and their original content using given ids.

    Args:
        hits: 待下载的 Hacker News ID | list of story IDs to download
        save_to_file: 是否保存 HTML 内容到文件 | Whether to save HTML content to files

    """

    current_date = datetime.datetime.now().date()
    html_texts = []

    target_dir = output_dir + f"{current_date.year}-{current_date.month}/"
    os.makedirs(target_dir, exist_ok=True)

    tasks = [
        asyncio.create_task(get_story(hit))
        for hit in hits
        # if not os.path.exists(os.path.join(target_dir, f"{hit['objectID']}.html"))
    ]
    stories = await asyncio.gather(*tasks)
    story_texts = []
    for idx, story in tqdm.tqdm(enumerate(stories), total=len(stories)):
        if save_to_file:
            generator.save_html(story, os.path.join(target_dir, f"{story['id']}.html"))

        html_text = generator.generate_html(story)
        story_texts.append((story.get("title", f"HN Story_{idx}"), html_text))

    origin_page_tasks = [
        asyncio.create_task(
            get_original_page(target_dir, hit["url"], hit["id"], save_to_file)
        )
        for hit in stories
    ]
    origin_pages = await asyncio.gather(*origin_page_tasks)

    for hn, ori in zip(story_texts, origin_pages):
        html_texts.append((hn[0], ori))
        html_texts.append(hn)

    return html_texts


def construct_epub_book(html_texts: list[str, str]):
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

    for i, (title, html_text) in tqdm.tqdm(
        enumerate(html_texts), total=len(html_texts)
    ):
        title = title or f"Story #{i+1}"
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

    result = f"<html><body><h1> ERROR </h1><br><a href={url}>{url}</a></body></html>"
    err_flag = False
    try:
        async with httpx.AsyncClient(timeout=20, verify=False) as client:
            blog_content, err_flag = await originSpider.get_origin(url, HEADERS)

            result = blog_content

            if result is None:
                print(
                    f"{url} 's trafilatura.extract() result is None. \n\n{blog_content[:1000]}"
                )
                result = f"<html><body><h1> ERROR </h1><br><a href={url}>{url}</a><p> result is None.</p></body></html>"

    except Exception as err:
        err_flag = True
        result = f"<html><body><h1> ERROR </h1><br><a href={url}>{url}</a><br><p>{str(err)}</p></body></html>"

    result = await embed_images_in_html_string(result, url)

    if save_flag:
        async with aiofiles.open(
            os.path.join(target_dir, f"{id}_ori.html"), "w+", encoding="utf-8"
        ) as fp:
            await fp.write(result)

    print(f"get original {str(url)[8:50]:>45} done. error?: {err_flag}")
    return result


if __name__ == "__main__":
    os.makedirs("outs/", exist_ok=True)

    start_time, end_time = asyncio.run(get_time_range_last_week())
    weekly = asyncio.run(search_stories_byTimeRange(25, start_time, end_time))
    weekly = [hit.get("objectID") for hit in weekly]

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
