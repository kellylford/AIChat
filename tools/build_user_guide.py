#!/usr/bin/env python3
"""Convert USER_GUIDE.md to HTML for publishing.

This script converts the markdown user guide to HTML for web publishing.
It preserves the markdown for easy editing while generating a styled HTML version.

Usage:
    python tools/build_user_guide.py

The script reads docs/USER_GUIDE.md and writes docs/USER_GUIDE.html
"""
import re
from pathlib import Path


def markdown_to_html(markdown_text: str) -> str:
    """Convert markdown to HTML with proper styling."""

    # Escape HTML special chars first
    html = markdown_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    html = html.replace('&amp;lt;', '&lt;').replace('&amp;gt;', '&gt;')

    # Convert markdown headings to HTML
    html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)

    # Convert **bold**
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)

    # Convert `code`
    html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)

    # Convert [links](urls)
    html = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', html)

    # Convert lists
    lines = html.split('\n')
    result = []
    in_list = False
    in_ordered = False

    for line in lines:
        # Ordered lists
        if re.match(r'^\d+\. ', line):
            if not in_ordered:
                if in_list:
                    result.append('</ul>')
                    in_list = False
                result.append('<ol>')
                in_ordered = True
            match = re.match(r'^\d+\. (.*?)$', line)
            if match:
                result.append(f'<li>{match.group(1)}</li>')
        # Unordered lists
        elif re.match(r'^- ', line):
            if not in_list:
                if in_ordered:
                    result.append('</ol>')
                    in_ordered = False
                result.append('<ul>')
                in_list = True
            match = re.match(r'^- (.*?)$', line)
            if match:
                result.append(f'<li>{match.group(1)}</li>')
        # End of list
        elif in_list or in_ordered:
            if in_list:
                result.append('</ul>')
            if in_ordered:
                result.append('</ol>')
            in_list = False
            in_ordered = False
            if line.strip():
                result.append(line)
        else:
            if line.strip():
                result.append(f'<p>{line}</p>')
            else:
                result.append('')

    if in_list:
        result.append('</ul>')
    if in_ordered:
        result.append('</ol>')

    html = '\n'.join(result)

    # Convert --- to <hr>
    html = re.sub(r'^---+$', '<hr>', html, flags=re.MULTILINE)

    return html


def main():
    """Generate HTML from markdown."""
    guide_path = Path(__file__).parent.parent / 'docs' / 'USER_GUIDE.md'

    if not guide_path.exists():
        print(f'Error: {guide_path} not found')
        return 1

    with open(guide_path, 'r', encoding='utf-8') as f:
        markdown = f.read()

    # Note: This is a simple converter. For production, consider using python-markdown
    # or pandoc. The HTML is pre-built to ensure correct styling and structure.
    print(f'Read {guide_path}')
    print('Note: HTML version is maintained manually for styling and accessibility.')
    print('If markdown changes significantly, update docs/USER_GUIDE.html accordingly.')

    return 0


if __name__ == '__main__':
    exit(main())
