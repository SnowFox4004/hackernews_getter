import asyncio
import base64
import os
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import httpx
from PIL import Image
from io import BytesIO


class HTMLImageEmbedder:
    def __init__(self, base_url, timeout=30, max_image_size=(1200, 1600)):
        self.base_url = base_url
        self.timeout = timeout
        self.max_image_size = max_image_size  # 适用于Kindle设备的最大图片尺寸
        self.client = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    def is_data_uri(self, src):
        """检查是否已经是data URI"""
        return src.startswith("data:")

    def is_absolute_url(self, src):
        """检查是否是绝对URL"""
        return bool(urlparse(src).netloc)

    def get_full_url(self, src):
        """获取完整的图片URL"""
        if self.is_data_uri(src) or not src:
            return None

        if self.is_absolute_url(src):
            return src
        else:
            return urljoin(self.base_url, src)

    def compress_image(self, image_data):
        """
        压缩图片大小
        :param image_data: 原始图片数据
        :param max_size: 最大尺寸 (width, height)
        :return: 压缩后的图片数据
        """
        image = Image.open(BytesIO(image_data))

        # 保存原始模式
        original_mode = image.mode

        # 按比例压缩图片
        if (
            image.size[0] > self.max_image_size[0]
            or image.size[1] > self.max_image_size[1]
        ):
            image.thumbnail(self.max_image_size, Image.Resampling.LANCZOS)
        # image.thumbnail(self.max_image_size, Image.Resampling.LANCZOS)

        # 保持图片模式不变，保留透明度
        output = BytesIO()
        # if image.format == "PNG" or original_mode in ("RGBA", "LA", "P"):
        #     # 对于PNG或带透明度的图片，保存为PNG格式以保留透明度
        #     image.save(output, format="PNG", optimize=True, compress_level=3)
        #     self.mime_type = "image/png"
        # else:
        #     # 对于其他格式，保存为JPEG
        #     image.save(output, format="JPEG", quality=85, optimize=True)
        #     self.mime_type = "image/jpeg"
        image.save(
            output, format=image.format or "JPEG", optimize=True, compress_level=5
        )

        compressed_data = output.getvalue()
        output.close()

        # 只有当压缩后的数据更小时才返回压缩后的数据
        if len(compressed_data) < len(image_data):
            return compressed_data
        else:
            return image_data

    async def download_image(self, url):
        """下载并压缩图片，返回base64编码的data URI"""
        try:
            response = await self.client.get(url, follow_redirects=True)
            response.raise_for_status()

            # 获取图片的MIME类型
            content_type = response.headers.get("content-type", "image/jpeg")
            if not content_type.startswith("image/"):
                content_type = self.guess_mime_type(url) or "image/jpeg"

            # 获取原始图片数据
            image_data = response.content

            try:
                # 使用新的压缩方法处理图片
                compressed_image_data = self.compress_image(image_data)
            except Exception as e:
                # 如果处理图片时出错，使用原始图片数据
                print(f"压缩图片失败 {str(url)[:50]}: {e}")
                compressed_image_data = image_data

            # 转换为base64
            image_data_base64 = base64.b64encode(compressed_image_data).decode("utf-8")
            return f"data:{content_type};base64,{image_data_base64}"

        except Exception as e:
            print(f"下载图片失败 {str(url)[:50]}: {e}")
            return None

    def guess_mime_type(self, url):
        """根据文件扩展名猜测MIME类型"""
        extension_to_mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".webp": "image/webp",
            ".ico": "image/x-icon",
        }

        path = urlparse(url).path
        ext = os.path.splitext(path)[1].lower()
        return extension_to_mime.get(ext)

    async def process_html(self, html_content):
        """处理HTML内容，嵌入图片"""
        soup = BeautifulSoup(html_content, "html.parser")
        img_tags = soup.find_all("img")
        graphic_tags = soup.find_all("graphic")
        figure_tags = soup.find_all("figure")

        img_tags.extend(graphic_tags)
        img_tags.extend(figure_tags)

        tasks = []
        img_data_map = {}

        # 收集所有需要下载的图片
        for img in img_tags:
            src = img.get("src", "")
            if not src or self.is_data_uri(src):
                continue

            full_url = self.get_full_url(src)
            if full_url:
                tasks.append((img, full_url))

        # 并发下载所有图片
        download_tasks = []
        url_to_task = {}

        for img, url in tasks:
            if url not in url_to_task:
                task = asyncio.create_task(self.download_image(url))
                url_to_task[url] = task
                download_tasks.append((url, task))

        # 等待所有下载完成
        for url, task in download_tasks:
            try:
                data_uri = await task
                if data_uri:
                    img_data_map[url] = data_uri
            except Exception as e:
                print(f"处理图片失败 {url}: {e}")

        # 替换img标签的src属性并将graphic标签转换为img标签
        for img, url in tasks:
            if url in img_data_map:
                img["src"] = img_data_map[url]
                # 如果是graphic标签，则替换为img标签
                if img.name != "img":
                    img.name = "img"
                print(f"成功嵌入图片: {url}")
            else:
                # print(f"保留原链接: {url}")
                pass

        return str(soup)

    async def process_html_string(self, html_string):
        """
        处理HTML字符串并返回处理后的HTML字符串

        Args:
            html_string: 输入的HTML字符串

        Returns:
            处理后的HTML字符串，其中图片已转换为base64内嵌格式
        """
        return await self.process_html(html_string)


async def embed_images_in_html(
    html_file_path, base_url, output_file_path=None, max_image_size=(1200, 1600)
):
    """
    主函数：将HTML文件中的图片转换为内嵌base64格式

    Args:
        html_file_path: 输入的HTML文件路径
        base_url: 原始页面的完整URL（用于处理相对路径）
        output_file_path: 输出文件路径，默认为原文件名加上_embedded
        max_image_size: 图片最大尺寸（宽，高），默认为(1200, 1600)适用于Kindle设备
    """

    if output_file_path is None:
        name, ext = os.path.splitext(html_file_path)
        output_file_path = f"{name}_embedded{ext}"

    # 读取HTML文件
    try:
        with open(html_file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
    except UnicodeDecodeError:
        with open(html_file_path, "r", encoding="gbk") as f:
            html_content = f.read()

    # 处理HTML
    async with HTMLImageEmbedder(base_url, max_image_size=max_image_size) as embedder:
        processed_html = await embedder.process_html(html_content)

    # 保存结果
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(processed_html)

    print(f"处理完成！输出文件: {output_file_path}")
    return output_file_path


async def embed_images_in_html_string(html_string, url, max_image_size=(1200, 1600)):
    """
    主函数：将HTML字符串中的图片转换为内嵌base64格式

    Args:
        html_string: 输入的HTML字符串
        url: 原始页面的完整URL
        max_image_size: 图片最大尺寸（宽，高），默认为(1200, 1600)适用于Kindle设备

    Returns:
        处理后的HTML字符串，其中图片已转换为base64内嵌格式
    """
    # 获取url根目录
    parsed_url = urlparse(url)
    url_root = str(parsed_url.scheme) + "://" + str(parsed_url.netloc)

    # 处理HTML
    async with HTMLImageEmbedder(url_root, max_image_size=max_image_size) as embedder:
        processed_html = await embedder.process_html_string(html_string)

    return processed_html


# 使用示例
async def main():
    # 请根据实际情况修改这些参数
    html_file_path = r"C:\Users\SnowFox4004\Desktop\程序\py\hackernews\stories\2025-9\45302065_ori.html"  # 输入的HTML文件路径
    base_url = "https://www.jeffgeerling.com/"  # 原始页面的完整URL
    output_file_path = "output_embedded.html"  # 输出文件路径（可选）

    await embed_images_in_html(html_file_path, base_url, output_file_path)


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())

# 简单使用方式（取消注释下面的代码并修改参数即可使用）
"""
async def simple_example():
    await embed_images_in_html(
        html_file_path="your_page.html",
        base_url="https://example.com/your-page",
        output_file_path="your_page_embedded.html"
    )

# asyncio.run(simple_example())
"""
