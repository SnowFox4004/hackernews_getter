"""
HTML Generator for Hacker News Stories to EPUB format
Generates clean HTML suitable for Kindle devices from Hacker News JSON data
"""

import json
from typing import Dict, List, Union, Optional
from utils import iso_to_string, convert_utc_to_local_v2


class HTMLGenerator:

    def __init__(self, max_depth: int = 5, max_comments_per_level: int | list = 4):
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
                f"  Posted: {convert_utc_to_local_v2(story_data.get('created_at', '1999-09-09T11:45:14.000Z'))}</p>",
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

    def _parse_hn_markup(self, text: str) -> str:
        r"""
        Parse Hacker News markup language and convert to HTML

        Hacker News markup rules:
        - Blank lines separate paragraphs
        - Text surrounded by asterisks is italicized
        - Use \* or ** for literal asterisk
        - Text after a blank line indented by 2+ spaces is verbatim (code)
        - URLs become links (except in submission text field)
        - URLs in <angle brackets> are linked correctly

        Args:
            text: Text with Hacker News markup

        Returns:
            HTML formatted text with proper spacing
        """
        if not text:
            return ""

        # Split by blank lines (two or more newlines)
        paragraphs = text.split('\n\n')
        html_parts = []

        for para in paragraphs:
            # Check if this is a code block (indented by 2+ spaces after blank line)
            # A code block is when ALL non-empty lines are indented by 2+ spaces
            # Use the original paragraph to preserve indentation info
            lines = para.split('\n')
            is_code_block = True

            for line in lines:
                stripped = line.lstrip()
                if stripped:  # Check non-empty lines
                    # Check if the line is indented by 2+ spaces or a tab
                    indent_len = len(line) - len(stripped)
                    if indent_len < 2:
                        is_code_block = False
                        break

            if is_code_block:
                # Code block - preserve formatting and add spacing
                # Preserve the original indentation in the code
                # Remove leading/trailing whitespace but keep internal structure
                para_content = para.strip()
                code_content = self._escape_html(para_content)
                html_parts.append(f' <pre><code>{code_content}</code></pre> ')
            else:
                # Regular paragraph - process inline markup
                # Strip the paragraph for regular text
                para_content = para.strip()
                if not para_content:
                    continue

                processed_lines = []
                for line in para_content.split('\n'):
                    processed_line = self._process_inline_markup(line)
                    processed_lines.append(processed_line)

                para_text = ' '.join(processed_lines)
                html_parts.append(f' <p>{para_text}</p> ')

        return ''.join(html_parts)

    def _process_inline_markup(self, line: str) -> str:
        """
        Process inline markup within a line (italics, URLs, escapes)

        Args:
            line: Single line of text

        Returns:
            Processed HTML line
        """
        if not line:
            return ""

        import re

        # First, handle escapes (\* for literal asterisk)
        # Need to process this before handling italics
        result = line.replace('\\*', 'ESCAPED_ASTERISK')

        # Handle URLs in <angle brackets> first - replace with a temporary marker
        # This prevents nested <a> tags
        def angle_bracket_url_replacer(match):
            url = match.group(1)
            # Create a unique marker
            marker = f'__URL_MARKER_{len(url)}_{hash(url)}__'
            # Store the URL for later replacement
            if not hasattr(self, '_url_markers'):
                self._url_markers = {}
            self._url_markers[marker] = url
            return f' {marker} '

        result = re.sub(r'<(https?://[^>]+)>', angle_bracket_url_replacer, result)

        # Handle regular URLs - convert to links
        def url_replacer(match):
            url = match.group(1)
            return f' <a href="{url}">{url}</a> '

        url_pattern = r'(https?://[^\s<>)\]]+)'
        result = re.sub(url_pattern, url_replacer, result)

        # Handle italics (*text*)
        # Need to find matching asterisk pairs
        result = self._parse_italics(result)

        # Convert URL markers back to links
        if hasattr(self, '_url_markers'):
            for marker, url in self._url_markers.items():
                result = result.replace(marker, f' <a href="{url}">{url}</a> ')
            self._url_markers.clear()

        # Convert escaped asterisks back
        result = result.replace('ESCAPED_ASTERISK', '*')

        return result

    def _parse_italics(self, text: str) -> str:
        """
        Parse italic markup (*text*) in text

        Args:
            text: Text to parse

        Returns:
            Text with italics converted to HTML
        """
        if not text:
            return ""

        result = []
        i = 0

        while i < len(text):
            char = text[i]

            if char == '*':
                # Check if this is the start or end of italic
                # Need to check if it's not followed by whitespace and not preceded by whitespace
                # Also need to handle ** as literal asterisk (already escaped to ESCAPED_ASTERISK)
                is_start = False
                is_end = False

                # Check if this could be start of italic
                if i + 1 < len(text) and text[i + 1] not in [' ', '\t', '\n', '*']:
                    # Look backward to see if we're not already in a word
                    if i == 0 or text[i - 1] in [' ', '\t', '\n', '<', '>']:
                        is_start = True

                # Check if this could be end of italic
                if i > 0 and text[i - 1] not in [' ', '\t', '\n', '*']:
                    # Look forward to see if we're ending a word
                    if i + 1 == len(text) or text[i + 1] in [' ', '\t', '\n', '<', '>']:
                        is_end = True

                if is_start:
                    result.append(' <i>')
                    i += 1
                elif is_end:
                    result.append('</i> ')
                    i += 1
                else:
                    # Lone asterisk, treat as literal
                    result.append('*')
                    i += 1
            else:
                result.append(char)
                i += 1

        return ''.join(result)

    def _format_text(self, text: str) -> str:
        """
        Format text for HTML display, handling Hacker News markup

        Args:
            text: Text to format

        Returns:
            Formatted HTML text
        """
        if not text:
            return ""

        # Parse Hacker News markup
        result = self._parse_hn_markup(text)

        return result

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
    generator = HTMLGenerator(max_depth=4, max_comments_per_level=[5, 2, 1, 1])

    # Load example data
    with open(r"example2.json", "r", encoding="utf-8") as f:
        story_data = json.load(f)
    #
    # # Generate and save HTML
    generator.save_html(story_data, "story.html")
    # pass
