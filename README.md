# HackerNews Scraper

本项目是一个用于抓取 [Hacker News](https://news.ycombinator.com/) 热门新闻的 Python 脚本。

## 功能

- 获取 Hacker News 首页新闻列表
- 支持新闻标题、链接、分数等信息的提取
- 支持保存为 EPUB PDF
- 在 `github action` 每周自动运

## 安装

1. 克隆本仓库：
    ```bash
    git clone https://github.com/yourusername/hackernews-scraper.git
    cd hackernews-scraper
    ```
2. 安装依赖：
    ```bash
    pip install -r requirements.txt
    ```

## 使用方法

```bash
python hacker_spider.py
```

## 依赖
详见 [pyproject.toml](pyproject.toml)
