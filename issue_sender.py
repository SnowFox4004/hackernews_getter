import requests
import os
import json
import dateutil
import time
import httpx

URL_ENDPOINT = "https://hn.algolia.com/api/v1"
HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
}


def get_weekly_titles(num_stories: int):
    SEARCH_ENDPOINT = "/search"
    search_url = URL_ENDPOINT + SEARCH_ENDPOINT

    hits = []
    page = 0
    with httpx.Client() as client:
        while len(hits) < num_stories:
            end_time = int(time.time())
            start_time = end_time - 60 * 60 * 24 * 7

            params = {
                "tags": "story",
                "numericFilters": f"created_at_i>{start_time},created_at_i<{end_time}",
                "page": page,
            }
            response = client.get(search_url, params=params)

            # print(
            #     f"Fetched {response.url} - {response.status_code}: {response.text if len(response.text) < 1000 else 'maybe normal'}"
            # )

            hits += response.json()["hits"]
            page += 1
    # import json

    # json.dump(hits, open("outs/hits.json", "w"))
    titles = list((hit["title"]) for hit in hits[:num_stories])
    urls = [
        f"https://news.ycombinator.com/item?id={hit['objectID']}"
        for hit in hits[:num_stories]
    ]
    return titles, urls


def send_issue_with_attachment(
    issue_body="This issue was created automatically by a GitHub Action. Please find the attached file for details.",
    file_path="outs/HackerNews.azw3",
    issue_title=(
        "Weekly HackerNews stories"
        + " @ "
        + dateutil.utils.today().strftime("%Y-%m-%d")
    ),
):
    print(f"creating issue: {issue_title} with attachment: {file_path}")
    # 配置信息
    token = os.getenv("GITHUB_TOKEN")  # 从环境变量读取令牌
    repo_owner = "SnowFox4004"  # 替换为你的仓库所有者
    repo_name = "hackernews_getter"  # 替换为你的仓库名

    # GitHub API 基础URL
    base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # 步骤1: 创建Issue
    create_issue_url = f"{base_url}/issues"
    issue_data = {"title": issue_title, "body": issue_body}

    response = requests.post(create_issue_url, headers=headers, json=issue_data)

    try:
        response.raise_for_status()
        issue_info = response.json()
        issue_number = issue_info["number"]
        print(f"Successfully created Issue #{issue_number}")
    except:
        print(f"Failed to create issue: {response.status_code}, {response.text}")

    # NOTE: 不支持上传azw3文件

    # # 步骤2: 上传文件到该Issue
    # # 首先，创建一个上传资源
    # upload_url = f"https://uploads.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_number}/assets"

    # # 删除Content-Type头部，让requests自动设置multipart/form-data及boundary
    # headers_upload = headers.copy()
    # if 'Content-Type' in headers_upload:
    #     del headers_upload['Content-Type']

    # # 使用multipart/form-data方式上传文件
    # with open(file_path, "rb") as file:
    #     files = {
    #         'file': (os.path.basename(file_path), file, 'application/octet-stream')
    #     }
    #     # 添加name参数到URL中
    #     params = {'name': os.path.basename(file_path)}
    #     response_upload = requests.post(upload_url, headers=headers_upload, files=files, params=params)

    # try:
    #     response_upload.raise_for_status()
    #     print(f"Successfully attached file to Issue #{issue_number}")
    # except:
    #     print(
    #         f"Failed to attach file: {response_upload.status_code}, {response_upload.text}"
    #     )


if __name__ == "__main__":
    titles, urls = get_weekly_titles(10)
    issue_body = "\n".join(
        f"- {title}\n[{url}]({url})" for title, url in zip(titles, urls)
    )

    send_issue_with_attachment(issue_body=issue_body)
