#!/usr/bin/env python3
"""
Generate HTML report from markdown source.
"""

import re
from pathlib import Path
from typing import List, Tuple


class MarkdownToHTML:
    """Convert markdown report to HTML with enhanced styling."""

    def __init__(self, md_path: str):
        self.md_path = Path(md_path)
        self.output_path = self.md_path.parent / "report.html"

    def convert(self) -> str:
        """Main conversion method."""
        # Read markdown
        with open(self.md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse content
        lines = content.split("\n")
        html_body = self._convert_body(lines)

        # Generate full HTML
        html = self._generate_html(html_body)

        # Write output
        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return html

    def _convert_body(self, lines: List[str]) -> str:
        """Convert markdown body to HTML."""
        sections = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Title (H1)
            if line.startswith("# "):
                sections.append(f"<h1>{self._escape_html(line[2:])}</h1>")
                i += 1

            # Meta info (italic)
            elif line.startswith("_") and line.endswith("_"):
                sections.append(f'<p class="meta">{self._escape_html(line[1:-1])}</p>')
                i += 1

            # Horizontal rule
            elif line.strip() == "---":
                sections.append("<hr />")
                i += 1

            # Section heading (H2)
            elif line.startswith("## "):
                sections.append(f"<h2>{self._escape_html(line[3:])}</h2>")
                i += 1

            # Images (handle multiple on one line)
            elif line.startswith("!["):
                html_imgs = self._convert_images(line)
                sections.append(html_imgs)
                i += 1

            # Tables
            elif line.startswith("|"):
                table_html, lines_consumed = self._convert_table(lines[i:])
                sections.append(table_html)
                i += lines_consumed

            # Ordered list
            elif re.match(r"^\d+\.", line.strip()):
                list_html, lines_consumed = self._convert_ordered_list(lines[i:])
                sections.append(list_html)
                i += lines_consumed

            # Unordered list
            elif line.strip().startswith("- "):
                list_html, lines_consumed = self._convert_unordered_list(lines[i:])
                sections.append(list_html)
                i += lines_consumed

            # Bold text blocks (summary values)
            elif line.startswith("**"):
                sections.append(self._convert_paragraph(line))
                i += 1

            # Regular paragraph
            elif line.strip() and not line.startswith((" ", "\t")):
                sections.append(self._convert_paragraph(line))
                i += 1

            # Empty line
            else:
                i += 1

        return "\n\n".join(sections)

    def _convert_images(self, line: str) -> str:
        """Convert image markdown to HTML."""
        # Match all images in the line
        img_pattern = r"!\[([^\]]*)\]\(([^\)]+)\)"
        images = re.findall(img_pattern, line)

        if len(images) > 1:
            # Multiple images - use grid layout
            imgs_html = []
            for alt, src in images:
                # Add chart class for chart images
                img_class = ' class="chart-image"' if "chart" in src.lower() else ""
                imgs_html.append(f'<img{img_class} src="{src}" alt="{alt}" />')
            return f'<div class="image-row">\n  {"  ".join(imgs_html)}\n</div>'
        elif len(images) == 1:
            # Single image
            alt, src = images[0]
            # Add chart class for chart images
            img_class = ' class="chart-image"' if "chart" in src.lower() else ""
            return f'<img{img_class} src="{src}" alt="{alt}" />'
        return ""

    def _convert_table(self, lines: List[str]) -> Tuple[str, int]:
        """Convert markdown table to HTML."""
        table_lines = []
        i = 0

        # Collect all table lines
        while i < len(lines) and lines[i].startswith("|"):
            table_lines.append(lines[i])
            i += 1

        if len(table_lines) < 2:
            return "", i

        # Parse table
        headers = [cell.strip() for cell in table_lines[0].split("|")[1:-1]]
        rows = []

        for line in table_lines[2:]:  # Skip separator line
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            rows.append(cells)

        # Build HTML
        html_parts = ["<table>", "  <thead>", "    <tr>"]
        for header in headers:
            html_parts.append(f"      <th>{self._escape_html(header)}</th>")
        html_parts.extend(["    </tr>", "  </thead>", "  <tbody>"])

        for row in rows:
            html_parts.append("    <tr>")
            for idx, cell in enumerate(row):
                # Handle HTML entities that should be preserved
                if cell == "—" or cell == "&mdash;":
                    html_parts.append(f"      <td>&mdash;</td>")
                else:
                    # Apply conditional styling
                    cell_class = self._get_cell_class(
                        headers[idx] if idx < len(headers) else "", cell
                    )
                    class_attr = f' class="{cell_class}"' if cell_class else ""
                    html_parts.append(
                        f"      <td{class_attr}>{self._escape_html(cell)}</td>"
                    )
            html_parts.append("    </tr>")

        html_parts.extend(["  </tbody>", "</table>"])

        return "\n".join(html_parts), i

    def _get_cell_class(self, header: str, cell: str) -> str:
        """Determine CSS class for conditional cell formatting."""
        # Highlight "Yes" cells
        if cell == "Yes":
            return "cell-yes"
        
        return ""

    def _convert_ordered_list(self, lines: List[str]) -> Tuple[str, int]:
        """Convert ordered list to HTML."""
        html_parts = ["<ol>"]
        i = 0

        while i < len(lines):
            line = lines[i].rstrip()

            # Check if line is empty
            stripped = line.lstrip()
            if not stripped:
                i += 1
                continue

            # Detect indentation
            indent = len(line) - len(stripped)

            # Check for list item (numbered or lettered)
            num_match = re.match(r"^(\d+)\.\s+(.+)$", stripped)
            letter_match = re.match(r"^([a-z])\)\s+(.+)$", stripped)

            if num_match:
                content = num_match.group(2)

                # Check if this is an indented item (nested list)
                if indent > 0:
                    # This shouldn't happen at the start, skip
                    break

                # Check if next line is indented (has nested items)
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    next_stripped = next_line.lstrip()
                    next_indent = len(next_line) - len(next_stripped)

                    if next_indent > 0 and re.match(r"^(\d+)\.\s+", next_stripped):
                        # Has nested numbered list
                        html_parts.append(f"  <li>{self._convert_inline(content)}")
                        html_parts.append("    <ol>")
                        i += 1

                        # Process nested items
                        while i < len(lines):
                            nested_line = lines[i]
                            nested_stripped = nested_line.lstrip()
                            nested_indent = len(nested_line) - len(nested_stripped)

                            if nested_indent == 0:
                                # Back to main level
                                break

                            nested_match = re.match(
                                r"^(\d+)\.\s+(.+)$", nested_stripped
                            )
                            if nested_match:
                                nested_content = nested_match.group(2)
                                html_parts.append(
                                    f"      <li>{self._convert_inline(nested_content)}</li>"
                                )
                                i += 1
                            else:
                                break

                        html_parts.append("    </ol>")
                        html_parts.append("  </li>")
                        continue

                # Regular list item
                html_parts.append(f"  <li>{self._convert_inline(content)}</li>")
                i += 1
            else:
                break

        html_parts.append("</ol>")
        return "\n".join(html_parts), i

    def _convert_unordered_list(self, lines: List[str]) -> Tuple[str, int]:
        """Convert unordered list to HTML."""
        html_parts = ["<ul>"]
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            if not line.startswith("- "):
                break

            content = line[2:]
            html_parts.append(f"  <li>{self._convert_inline(content)}</li>")
            i += 1

        html_parts.append("</ul>")
        return "\n".join(html_parts), i

    def _convert_paragraph(self, line: str) -> str:
        """Convert paragraph with inline formatting."""
        content = self._convert_inline(line)
        return f"<p>{content}</p>"

    def _convert_inline(self, text: str) -> str:
        """Convert inline markdown formatting."""
        # Remove markdown escape characters
        text = text.replace("\\$", "$")
        text = text.replace("\\>", ">")
        # Bold - convert ** to <strong> tags
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        return text

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters while preserving some entities."""
        # Don't escape if it already contains HTML entities
        if "&mdash;" in text or "&gt;" in text:
            return text

        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        return text

    def _generate_html(self, body: str) -> str:
        """Generate complete HTML document."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>3904 Petes Path Valuation</title>
  <style>
    {self._get_css()}
  </style>
</head>
<body>
  <main class="page">
    {body}
  </main>
</body>
</html>"""

    def _get_css(self) -> str:
        """Return enhanced CSS styling."""
        return """* {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      line-height: 1.6;
      background-color: #f8f9fb;
      color: #1f2933;
    }

    .page {
      max-width: 2000px;
      margin: 0 auto;
      padding: 48px 24px 72px;
      background-color: #ffffff;
    }

    h1 {
      margin-top: 0;
      font-size: 2.25rem;
    }

    h2 {
      font-size: 1.5rem;
      border-bottom: 2px solid #e5e7eb;
      padding-bottom: 0.35rem;
      margin-top: 1.8em;
      margin-bottom: 0.6em;
      line-height: 1.25;
    }

    h3 {
      font-size: 1.2rem;
      margin-top: 1.8em;
      margin-bottom: 0.6em;
      line-height: 1.25;
    }

    .meta {
      color: #4b5563;
      font-style: italic;
    }

    p {
      margin: 0.75em 0;
    }

    hr {
      margin: 2.5rem 0;
      border: 0;
      border-top: 1px solid #e5e7eb;
    }

    ul {
      padding-left: 1.25rem;
      margin: 0.75em 0;
    }

    ol {
      padding-left: 1.25rem;
      margin: 0.75em 0;
    }

    li + li {
      margin-top: 0.25em;
    }

    strong {
      font-weight: 600;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      margin: 1.5rem 0;
      font-size: 0.9rem;
    }

    thead {
      background-color: #f1f5f9;
    }

    th {
      border: 1px solid #d1d5db;
      padding: 0.5rem 0.6rem;
      text-align: left;
      font-weight: 600;
      color: #111827;
    }

    td {
      border: 1px solid #d1d5db;
      padding: 0.5rem 0.6rem;
      text-align: left;
      vertical-align: top;
    }

    tbody tr:nth-child(odd) {
      background-color: #f9fafb;
    }

    /* Conditional cell highlighting */
    .cell-yes {
      background-color: #e0f2fe !important;
    }

    img {
      max-width: 100%;
      height: auto;
      display: block;
      margin: 1.25rem 0;
      border-radius: 8px;
      box-shadow: 0 6px 20px rgba(15, 23, 42, 0.12);
    }

    img.chart-image {
      width: 100%;
      max-width: 1200px;
    }

    .image-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 1.5rem;
      margin: 1.5rem 0;
    }

    .image-row img {
      margin: 0;
    }

    @media (max-width: 640px) {
      .page {
        padding: 32px 18px 56px;
        max-width: 100%;
      }

      table {
        font-size: 0.82rem;
      }

      th, td {
        padding: 0.45rem 0.5rem;
      }

      h1 {
        font-size: 1.9rem;
      }
    }

    @media print {
      .page {
        max-width: 100%;
        padding: 20px;
      }

      h2 {
        page-break-after: avoid;
      }

      table {
        page-break-inside: avoid;
      }
    }"""


def main():
    """Main entry point."""
    converter = MarkdownToHTML("report.md")
    converter.convert()
    print("✓ Generated report.html")


if __name__ == "__main__":
    main()
