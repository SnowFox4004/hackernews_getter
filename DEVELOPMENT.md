# 开发指南

本文档面向开发者，介绍如何为项目添加新功能和扩展现有能力。

## 添加新的 Origin Page 处理器

项目使用注册表模式处理不同域名的原始页面获取。你可以为特定域名添加自定义处理器。

### 处理器接口规范

所有处理器必须遵循相同的函数签名：

```python
async def handler(url: str, headers: dict) -> tuple[str, bool]:
    """
    Args:
        url: 目标页面 URL
        headers: HTTP 请求头

    Returns:
        content: str - 提取的 HTML 内容
        is_error: bool - 是否发生错误
    """
```

### 添加新处理器步骤

#### 1. 创建处理器文件

在 `src/hackernews/handlers/` 目录下创建新的 Python 文件：

```
src/hackernews/handlers/
├── __init__.py    # 注册表核心
├── default.py     # 默认处理器
├── xcancel.py     # x.com/twitter.com 处理器
└── your_site.py   # 你的新处理器
```

#### 2. 实现处理器

```python
# handlers/your_site.py

from __future__ import annotations

from handlers import register_handler
from handlers.default import default_handler


@register_handler("example.com")
@register_handler("www.example.com")  # 可注册多个域名
async def example_handler(url: str, headers: dict) -> tuple[str, bool]:
    """处理 example.com 域名的页面获取。

    Args:
        url: 目标 URL
        headers: HTTP 请求头

    Returns:
        Tuple of (content, is_error)
    """
    # 方式1: 直接使用默认处理器
    return await default_handler(url, headers)

    # 方式2: 自定义逻辑后调用默认处理器
    # new_url = url.replace("example.com", "api.example.com")
    # return await default_handler(new_url, headers)

    # 方式3: 完全自定义实现
    # content = await your_custom_fetch_logic(url, headers)
    # return content, False
```

#### 3. 在注册表中导入

编辑 `handlers/__init__.py`，添加导入语句：

```python
# 在文件末尾的导入区域添加
from handlers import default, xcancel, your_site  # 添加 your_site

__all__ = [
    # ...
    "your_site",  # 添加到导出列表
]
```

#### 4. 测试处理器

```python
import asyncio
from origin_page_spider import get_origin

# 测试新处理器
result = asyncio.run(get_origin(
    "https://example.com/some-page",
    {"User-Agent": "test"}
))
print(f"Content length: {len(result[0])}, Is error: {result[1]}")
```

### 示例：xcancel 处理器

以下是一个完整的处理器示例，将 x.com/twitter.com 重定向到 xcancel.com：

```python
# handlers/xcancel.py

from __future__ import annotations

import re

from handlers import register_handler
from handlers.default import default_handler


@register_handler("x.com")
@register_handler("twitter.com")
async def xcancel_handler(url: str, headers: dict) -> tuple[str, bool]:
    """Handle x.com and twitter.com URLs by redirecting to xcancel.com."""
    # 替换域名
    new_url = re.sub(
        r'^(https?://)(?:x|twitter)\.com',
        r'\1xcancel.com',
        url
    )

    print(f"Redirecting: {url} -> {new_url}")

    # 使用默认处理器获取内容
    return await default_handler(new_url, headers)
```

### 默认处理器功能

`default_handler` 提供以下功能：

1. **HTTP 请求**: 使用 httpx 发送异步请求
2. **内容提取**: 使用 trafilatura 提取正文
3. **Playwright 回退**: 内容过短时使用浏览器渲染
4. **HTML 合并**: 合并多种方法的结果

你可以直接调用它作为基础，也可以完全自定义实现。

### 域名匹配规则

- **精确匹配**: 只匹配完全相同的域名
- `x.com` 只匹配 `x.com`，不匹配 `api.x.com`
- 如需匹配多个域名，需分别注册

### 错误处理

处理器应正确返回错误状态：

```python
# 成功
return content_html, False

# 失败
return f"<h1>ERROR</h1><p>Error: {error}</p>", True
```

### 调试技巧

1. 查看已注册的域名：
```python
from handlers import list_registered_domains
print(list_registered_domains())
# 输出: ['twitter.com', 'x.com']
```

2. 检查处理器匹配：
```python
from handlers import get_handler
handler = get_handler("https://x.com/status/123")
print(handler.__name__)  # 输出: xcancel_handler
```

## 其他开发说明

### 运行测试

```bash
# 运行主爬虫
uv run src/hackernews/hacker_spider.py

# 使用 CLI 工具
uv run src/hackernews/hngtr.py search --last_week -n 10
```

### 代码风格

- Python 3.12+ 语法
- 使用 async/await 异步模式
- 类型提示（`tuple[str, bool]` 而非 `Tuple[str, bool]`）
- Google 风格 docstring
