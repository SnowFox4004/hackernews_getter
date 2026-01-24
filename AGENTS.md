# Agent Guidelines for hackernews_getter

This document provides essential information for agentic coding agents working in this repository.

## Project Overview

A Python-based Hacker News scraper that fetches stories, downloads original content, and generates EPUB/PDF output. The project uses async HTTP requests, Playwright for dynamic content, and GitHub Actions for weekly automation.

## Development Commands

### Build & Installation
```bash
# Install dependencies using uv
uv sync

# Install Playwright browsers
uv run python -m playwright install --with-deps
```

### Running the Code
```bash
# Run main scraper (weekly digest)
uv run src/hackernews/hacker_spider.py

# Run CLI tool
uv run src/hackernews/hngtr.py
uv run src/hackernews/hngtr.py search --num 10 --last_week
uv run src/hackernews/hngtr.py download 12345 12346 -o ./output

# Run monthly trend script
uv run src/hackernews/month_trend.py
```

### Testing & Linting
This project does not currently have automated tests or linting configured. When implementing new features, manually test by running the relevant scripts listed above.

## Code Style Guidelines

### Import Organization
```python
# 1. Standard library imports
import asyncio
import datetime
import os
import html

# 2. Third-party imports
import httpx
import aiofiles
from bs4 import BeautifulSoup
import trafilatura
from dateutil import parser

# 3. Local imports (from src/hackernews/)
from utils import get_time_range_last_week
from hacker_spider import search_stories_byTimeRange
```

### Type Hints
- Requires Python 3.12+
- Use modern union syntax: `int | list` instead of `Union[int, list]`
- Type all function parameters and return values
- Use `typing` module for complex types: `Dict[str, Any]`, `List[Tuple[str, str]]`

```python
async def search_stories(num_stories: int, start_time: int, end_time: int) -> list[dict]:
    pass

def parse_timestamp(timestamp: str) -> datetime.datetime:
    pass
```

### Naming Conventions
- **Functions/variables**: `snake_case` (e.g., `get_time_range_last_week`, `html_text`)
- **Classes**: `PascalCase` (e.g., `HTMLGenerator`, `HTMLImageEmbedder`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `URL_ENDPOINT`, `HEADERS`)
- **Type aliases**: `PascalCase` (e.g., `StoryData`, `HTMLContent`)

### Async Patterns
```python
# Create tasks for parallel execution
tasks = [asyncio.create_task(get_story(hit)) for hit in hits]
results = await asyncio.gather(*tasks)

# Use context managers for async clients
async with httpx.AsyncClient() as client:
    response = await client.get(url)
```

### Error Handling
- Use try-except blocks for network operations
- Return error indicators (e.g., `is_error: bool`) for non-critical failures
- Print informative error messages with context (URL, timestamp)
- Never silently swallow exceptions in critical paths

```python
async def fetch_content(url: str):
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None
```

### Docstrings
Use Google-style docstrings with Args and Returns sections:
```python
def process_stories(stories: list[dict], output_dir: str) -> str:
    """Process Hacker News stories and save to directory.

    Args:
        stories: List of story dictionaries from HN API
        output_dir: Directory path to save processed files

    Returns:
        Path to generated output file
    """
```

### HTML/CSS in Python
- Use multi-line strings for HTML templates
- Keep CSS minimal and self-contained for EPUB compatibility
- Use inline styles when targeting specific readers (Kindle)
- Escape user content with `_escape_html()` before embedding

### Project Structure
```
src/hackernews/
├── __init__.py
├── main.py              # Entry point
├── hngtr.py             # CLI tool (rich-click)
├── hacker_spider.py     # Core fetching logic
├── html_generator.py    # HN story → HTML conversion
├── html_img_embedder.py # Image extraction & embedding
├── origin_page_spider.py # Original content fetching
├── concat_htmls.py      # PDF generation (WeasyPrint)
├── utils.py             # Date/time utilities
├── month_trend.py       # Monthly digest generation
└── issue_sender.py      # GitHub issue creation
```

### Output Directories
- `stories/` - Raw HTML files (gitignored, organized by year-month)
- `outs/` - Final EPUB/PDF files (gitignored)
- Generated files should not be committed to git

### Configuration
- Dependencies managed via `pyproject.toml` with uv
- Python version: 3.12+
- Playwright browsers must be installed separately

### GitHub Actions
- Weekly cron job runs every Sunday (00:00 UTC)
- Manual dispatch available via Actions tab
- Outputs uploaded as artifacts (7-day retention)
- Creates GitHub issue for monthly digest

## When Making Changes

1. Async functions should use timeouts on all HTTP requests
2. When modifying HTML generation, test EPUB output on real e-reader
3. Image embedding respects max size of (900, 1200) for Kindle compatibility
4. Always handle network failures gracefully - don't fail entire batch on single error
5. Add new CLI commands to `hngtr.py` using rich-click decorators
6. For new file formats, update the `.gitignore` accordingly
