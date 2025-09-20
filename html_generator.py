"""
HTML Generator for Hacker News Stories to EPUB format
Generates clean HTML suitable for Kindle devices from Hacker News JSON data
"""

import json
from typing import Dict, List, Union, Optional


class HTMLGenerator:
    def __init__(self, max_depth: int = 5, max_comments_per_level: int | list = 10):
        """
        Initialize the HTML generator with configurable options

        Args:
            max_depth: Maximum depth of comments to include
            max_comments_per_level: Maximum number of comments per level to include
        """
        self.max_depth = max_depth

        if isinstance(max_comments_per_level, int):
            self.max_comments_per_level = [max_comments_per_level] * self.max_depth
        elif isinstance(max_comments_per_level, list):
            assert (
                len(max_comments_per_level) == self.max_depth
            ), "Length of max_comments_per_level must match max_depth"
            self.max_comments_per_level = max_comments_per_level
        else:
            raise ValueError()
        # self.max_comments_per_level = max_comments_per_level

    def generate_html(self, story_data: Dict) -> str:
        """
        Generate HTML from story data

        Args:
            story_data: Dictionary containing the story data from Hacker News API

        Returns:
            String containing the generated HTML
        """
        html = [
            "<!DOCTYPE html>",
            '<html lang="en">',
            "<head>",
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            "    <title>"
            + self._escape_html(story_data.get("title", "Hacker News Story"))
            + "</title>",
            "    <style>",
            "        body {",
            "            font-family: Georgia, serif;",
            "            font-size: 12pt;",
            "            line-height: 1.4;",
            "            margin: 20px;",
            "            color: #000000;",
            "        }",
            "        h1 {",
            "            font-size: 18pt;",
            "        }",
            "        .story-info {",
            "            font-size: 10pt;",
            "            color: #666666;",
            "            margin: 10px 0;",
            "        }",
            "        .comment {",
            "            border-left: 1px solid #cccccc;",
            "            margin: 10px 0;",
            "            padding-left: 10px;",
            "        }",
            "        .comment-header {",
            "            font-size: 10pt;",
            "            font-weight: bold;",
            "            margin-bottom: 5px;",
            "        }",
            "        .comment-text {",
            "            margin: 5px 0;",
            "        }",
            "        .comment-level-0 { margin-left: 0; }",
            "        .comment-level-1 { margin-left: 20px; }",
            "        .comment-level-2 { margin-left: 40px; }",
            "        .comment-level-3 { margin-left: 60px; }",
            "        .comment-level-4 { margin-left: 80px; }",
            "        .comment-level-5 { margin-left: 100px; }",
            "    </style>",
            "</head>",
            "<body>",
        ]

        # Add story title and info
        html.extend(
            [
                f"<a href='{story_data.get('url', '#')}'>jump to url</a>"
                f"<h1>{self._escape_html(story_data.get('title', 'Untitled'))}</h1>",
                f'<div class="story-info">',
                f"  <p>Author: {self._escape_html(story_data.get('author', 'Unknown'))} | ",
                f"  Points: {story_data.get('points', 0)} | ",
                f"  Posted: {story_data.get('created_at', '')}</p>",
                f"</div>",
            ]
        )

        # Add story text if available
        story_text = story_data.get("text")
        if story_text:
            html.append(
                f'<div class="story-text">{self._format_text(story_text)}</div>'
            )

        # Add comments
        children = story_data.get("children", [])
        html.append('<div class="comments-section">')
        html.append("<h2>Comments</h2>")
        html.append(self._generate_comments_html(children, 0))
        html.append("</div>")

        # Close HTML
        html.extend(["</body>", "</html>"])

        return "\n".join(html)

    def _generate_comments_html(self, comments: List[Dict], level: int) -> str:
        """
        Generate HTML for comments recursively

        Args:
            comments: List of comment dictionaries
            level: Current nesting level

        Returns:
            String containing the generated HTML for comments
        """
        if level >= self.max_depth:
            return ""

        html = []
        comments_to_process = comments[: self.max_comments_per_level[level]]

        for comment in comments_to_process:
            # Comment header with author and metadata
            html.extend(
                [
                    f'<div class="comment comment-level-{level}">',
                    f'  <div class="comment-header">',
                    f"    {self._escape_html(comment.get('author', 'Anonymous'))}",
                    f"  </div>",
                ]
            )

            # Comment text
            comment_text = comment.get("text")
            if comment_text:
                html.append(
                    f'  <div class="comment-text">{self._format_text(comment_text)}</div>'
                )

            # Process child comments recursively
            children = comment.get("children", [])
            if children and level < self.max_depth - 1:
                html.append(self._generate_comments_html(children, level + 1))

            html.append("</div>")

        return "\n".join(html)

    def _escape_html(self, text: str) -> str:
        """
        Escape HTML special characters

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        if not text:
            return ""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

    def _format_text(self, text: str) -> str:
        """
        Format text for HTML display, handling basic markup

        Args:
            text: Text to format

        Returns:
            Formatted HTML text
        """
        if not text:
            return ""

        # Handle basic HTML tags that might be in the text
        # Convert paragraph markers
        if "<p>" in text:
            if not text.startswith("<p>"):
                text = "<p>" + text
            text = text.replace("<p>", "</p><p>")
        # text = self._escape_html(text)
        # Handle links - this is a simplified approach
        # text = text.replace("<a href=", "<a href=")
        # Preserve line breaks
        text = text.replace("\n", "<br>")

        return text

    def save_html(self, story_data: Dict, filename: str):
        """
        Generate HTML from story data and save to file

        Args:
            story_data: Dictionary containing the story data
            filename: Output filename
        """
        html_content = self.generate_html(story_data)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)


# Example usage
if __name__ == "__main__":
    # Example of how to use the HTMLGenerator
    generator = HTMLGenerator(max_depth=4, max_comments_per_level=[8, 6, 3, 1])

    # Load example data
    with open(r"example2.json", "r", encoding="utf-8") as f:
        story_data = json.load(f)
    #
    # # Generate and save HTML
    generator.save_html(story_data, "story.html")
    # pass
