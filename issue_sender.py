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


def get_titles_byTimeRange(num_stories: int, start_time: int, end_time: int):
    SEARCH_ENDPOINT = "/search"
    search_url = URL_ENDPOINT + SEARCH_ENDPOINT

    hits = []
    page = 0
    with httpx.Client() as client:
        while len(hits) < num_stories:
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


def send_issue(
    issue_body="This issue was created automatically by a GitHub Action. Please find the attached file for details.",
    file_path="outs/HackerNews.azw3",
    issue_title=(
        "Weekly HackerNews stories"
        + " @ "
        + dateutil.utils.today().strftime("%Y-%m-%d")
    ),
    labels=None,
):
    print(f"creating issue: {issue_title} with attachment: {file_path}")
    # 配置信息
    token = os.getenv("CLIENT_TOKEN")  # 从环境变量读取令牌

    # ################
    # # debug
    # import hashlib

    # token_sha256 = hashlib.sha256(token.encode()).hexdigest()
    # print(f"Using token with SHA256: {token_sha256}")
    # exit(0)
    # # debug end
    # ################

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

        # 如果提供了标签，则为issue添加标签
        if labels and isinstance(labels, list) and len(labels) > 0:
            # 使用GitHub API为issue添加标签
            labels_url = f"{base_url}/issues/{issue_number}/labels"
            labels_data = {"labels": labels}
            labels_response = requests.post(
                labels_url, headers=headers, json=labels_data
            )

            try:
                labels_response.raise_for_status()
                print(f"Successfully added labels {labels} to Issue #{issue_number}")
            except:
                print(
                    f"Failed to add labels: {labels_response.status_code}, {labels_response.text}"
                )

    except:
        print(f"Failed to create issue: {response.status_code}, {response.text}")


if __name__ == "__main__":
    start_time = int(time.time()) - 7 * 24 * 3600
    end_time = int(time.time())

    titles, urls = get_titles_byTimeRange(10, start_time, end_time)
    issue_body = "\n".join(
        f"- {title}\n[{url}]({url})" for title, url in zip(titles, urls)
    )

    send_issue(issue_body=issue_body, labels=["weekly", "automated"])
