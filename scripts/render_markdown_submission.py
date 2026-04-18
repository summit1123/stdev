#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8') if path.exists() else ''


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def extract_preset(design_text: str) -> str:
    match = re.search(r'(?mi)^Preset:\s*([A-Za-z0-9_-]+)\s*$', design_text or '')
    return match.group(1).strip().lower() if match else 'document-editorial'


def extract_reference_pack(design_text: str) -> str:
    match = re.search(r'(?mi)^Reference-Pack:\s*([A-Za-z0-9_-]+)\s*$', design_text or '')
    return match.group(1).strip().lower() if match else ''


REFERENCE_PACK_TOKENS = {
    'editorial-signal': {'accent': '#1f6f64', 'surface': '#f4f4f1', 'surface_strong': '#eceae4', 'page_bg': 'white'},
    'security-console': {'accent': '#8a3b2f', 'surface': '#f6f2ef', 'surface_strong': '#ece4dd', 'page_bg': '#fcfbfa'},
    'analyst-workbench': {'accent': '#355c7d', 'surface': '#f3f5f7', 'surface_strong': '#e5eaef', 'page_bg': '#fcfcfd'},
    'citizen-service': {'accent': '#005f73', 'surface': '#f1f6f7', 'surface_strong': '#e0ecef', 'page_bg': 'white'},
    'devtool-minimal': {'accent': '#334155', 'surface': '#f4f5f6', 'surface_strong': '#e7eaee', 'page_bg': '#fcfcfc'},
    'consumer-trust': {'accent': '#0f766e', 'surface': '#f2f7f6', 'surface_strong': '#e3efed', 'page_bg': 'white'},
}


def reference_pack_tokens(reference_pack: str) -> dict[str, str]:
    return REFERENCE_PACK_TOKENS.get(reference_pack or '', {})


def extract_title(markdown_text: str) -> str:
    for line in (markdown_text or '').splitlines():
        stripped = line.strip()
        if stripped.startswith('# '):
            return stripped[2:].strip()
    return 'Submission Document'


def stash_html(raw: str, bucket: list[str]) -> str:
    token = f'CODEXHTMLTOKEN{len(bucket)}'
    bucket.append(raw)
    return token


def inline_markup(text: str) -> str:
    bucket: list[str] = []
    staged = text or ''
    staged = re.sub(
        r'!\[([^\]]*)\]\(([^)]+)\)',
        lambda m: stash_html(
            f'<img src="{html.escape(m.group(2), quote=True)}" alt="{html.escape(m.group(1))}" />',
            bucket,
        ),
        staged,
    )
    staged = re.sub(
        r'\[([^\]]+)\]\(([^)]+)\)',
        lambda m: stash_html(
            f'<a href="{html.escape(m.group(2), quote=True)}">{html.escape(m.group(1))}</a>',
            bucket,
        ),
        staged,
    )
    staged = html.escape(staged)
    staged = re.sub(r'`([^`]+)`', lambda m: f'<code>{m.group(1)}</code>', staged)
    staged = re.sub(r'\*\*([^*]+)\*\*', lambda m: f'<strong>{m.group(1)}</strong>', staged)
    staged = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', lambda m: f'<em>{m.group(1)}</em>', staged)
    for index, value in enumerate(bucket):
        staged = staged.replace(f'CODEXHTMLTOKEN{index}', value)
    return staged


def is_table_divider(line: str) -> bool:
    stripped = line.strip()
    return bool(re.fullmatch(r'\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?', stripped))


def split_table_row(line: str) -> list[str]:
    stripped = line.strip().strip('|')
    return [cell.strip() for cell in stripped.split('|')]


def block_starts(lines: list[str], index: int) -> bool:
    if index >= len(lines):
        return False
    line = lines[index]
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith('```'):
        return True
    if re.match(r'^#{1,6}\s+', stripped):
        return True
    if re.match(r'^[-*_]{3,}\s*$', stripped):
        return True
    if re.match(r'^(?:[-*+]\s+|\d+\.\s+)', stripped):
        return True
    if stripped.startswith('>'):
        return True
    if index + 1 < len(lines) and '|' in line and is_table_divider(lines[index + 1]):
        return True
    return False


def markdown_to_html(markdown_text: str) -> str:
    lines = markdown_text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    blocks: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        if stripped.startswith('```'):
            language = stripped[3:].strip()
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            class_attr = f' class="language-{html.escape(language)}"' if language else ''
            blocks.append(f'<pre><code{class_attr}>{html.escape("\n".join(code_lines))}</code></pre>')
            continue

        heading = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if heading:
            level = len(heading.group(1))
            blocks.append(f'<h{level}>{inline_markup(heading.group(2).strip())}</h{level}>')
            i += 1
            continue

        if re.match(r'^[-*_]{3,}\s*$', stripped):
            blocks.append('<hr />')
            i += 1
            continue

        if i + 1 < len(lines) and '|' in line and is_table_divider(lines[i + 1]):
            header = split_table_row(line)
            i += 2
            rows: list[list[str]] = []
            while i < len(lines):
                row_line = lines[i]
                if not row_line.strip() or '|' not in row_line:
                    break
                rows.append(split_table_row(row_line))
                i += 1
            header_html = ''.join(f'<th>{inline_markup(cell)}</th>' for cell in header)
            row_html = []
            for row in rows:
                row_html.append('<tr>' + ''.join(f'<td>{inline_markup(cell)}</td>' for cell in row) + '</tr>')
            blocks.append('<table><thead><tr>' + header_html + '</tr></thead><tbody>' + ''.join(row_html) + '</tbody></table>')
            continue

        list_match = re.match(r'^(?P<indent>\s*)(?P<marker>[-*+]|\d+\.)\s+(?P<body>.*)$', line)
        if list_match:
            ordered = list_match.group('marker').endswith('.') and list_match.group('marker')[0].isdigit()
            tag = 'ol' if ordered else 'ul'
            items: list[str] = []
            while i < len(lines):
                current = lines[i]
                current_match = re.match(r'^(?P<indent>\s*)(?P<marker>[-*+]|\d+\.)\s+(?P<body>.*)$', current)
                if not current_match:
                    break
                current_ordered = current_match.group('marker').endswith('.') and current_match.group('marker')[0].isdigit()
                if current_ordered != ordered:
                    break
                items.append(f'<li>{inline_markup(current_match.group("body").strip())}</li>')
                i += 1
            blocks.append(f'<{tag}>' + ''.join(items) + f'</{tag}>')
            continue

        if stripped.startswith('>'):
            quote_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                quote_lines.append(re.sub(r'^\s*>\s?', '', lines[i]))
                i += 1
            blocks.append(f'<blockquote>{markdown_to_html("\n".join(quote_lines))}</blockquote>')
            continue

        paragraph_lines = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and not block_starts(lines, i):
            paragraph_lines.append(lines[i].strip())
            i += 1
        blocks.append(f'<p>{inline_markup(" ".join(paragraph_lines))}</p>')
    return '\n'.join(blocks)


def document_styles(preset: str, reference_pack: str = '') -> str:
    tokens = reference_pack_tokens(reference_pack)
    accent = tokens.get('accent', '#1f6f64')
    surface = tokens.get('surface', '#f4f4f1')
    surface_strong = tokens.get('surface_strong', '#eceae4')
    page_bg = tokens.get('page_bg', 'white')
    common = """
:root {
  --ink: #111111;
  --muted: #5b5b5b;
  --line: #cfcfcf;
  --surface: __SURFACE__;
  --surface-strong: __SURFACE_STRONG__;
  --accent: __ACCENT__;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Noto Sans KR', 'Segoe UI', sans-serif;
  color: var(--ink);
  background: __PAGE_BG__;
  line-height: 1.65;
  font-size: 15px;
}
.page {
  width: min(960px, calc(100vw - 96px));
  margin: 0 auto;
  padding: 56px 0 72px;
}
h1, h2, h3, h4 {
  color: var(--ink);
  line-height: 1.2;
  letter-spacing: 0;
  margin: 0 0 14px;
  font-weight: 800;
}
h1 {
  font-size: 34px;
  margin-top: 8px;
  padding-top: 6px;
  border-top: 4px solid var(--ink);
}
h2 {
  font-size: 24px;
  margin-top: 42px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}
h3 {
  font-size: 18px;
  margin-top: 30px;
}
p, li, td, th, blockquote { word-break: keep-all; }
p, ul, ol, table, pre, blockquote { margin: 0 0 18px; }
ul, ol { padding-left: 22px; }
li + li { margin-top: 6px; }
table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
th, td {
  border: 1px solid var(--line);
  padding: 12px 14px;
  vertical-align: top;
  text-align: left;
}
th {
  background: var(--surface-strong);
  font-weight: 700;
}
td { background: white; }
blockquote {
  margin-left: 0;
  padding: 14px 18px;
  border-left: 4px solid var(--accent);
  background: var(--surface);
}
code {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.92em;
  background: #f1f1f1;
  padding: 0.1em 0.35em;
  border-radius: 4px;
}
pre {
  overflow-x: auto;
  background: #151515;
  color: #f5f5f5;
  padding: 18px;
  border-radius: 6px;
}
pre code {
  background: transparent;
  padding: 0;
  color: inherit;
}
a { color: var(--ink); text-decoration-thickness: 1px; }
img {
  display: block;
  width: 100%;
  height: auto;
  border: 1px solid var(--line);
  border-radius: 6px;
  margin: 8px 0 18px;
}
hr {
  border: 0;
  border-top: 1px solid var(--line);
  margin: 28px 0;
}
.eyebrow {
  display: inline-block;
  margin-bottom: 16px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
@page {
  size: A4;
  margin: 16mm 15mm 16mm 15mm;
}
@media print {
  .page {
    width: auto;
    padding: 0;
  }
  h1, h2, h3, table, blockquote, pre, img {
    break-inside: avoid;
  }
}
"""
    common = (
        common.replace('__ACCENT__', accent)
        .replace('__SURFACE__', surface)
        .replace('__SURFACE_STRONG__', surface_strong)
        .replace('__PAGE_BG__', page_bg)
    )
    if preset == 'product-ops':
        return common + """
h1 {
  border-top-color: var(--accent);
}
h2 {
  border-top-color: color-mix(in srgb, var(--accent) 30%, white);
}
"""
    return common

def build_html_document(title: str, body_html: str, preset: str, reference_pack: str = '') -> str:
    reference_note = f' / {reference_pack}' if reference_pack else ''
    return f'''<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html.escape(title)}</title>
    <style>{document_styles(preset, reference_pack)}</style>
  </head>
  <body>
    <main class="page">
      <div class="eyebrow">SummitHarness Render{html.escape(reference_note)}</div>
      {body_html}
    </main>
  </body>
</html>
'''


def chrome_binary() -> str | None:
    env_value = os.environ.get('CHROME_BIN')
    candidates = [
        env_value,
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Chromium.app/Contents/MacOS/Chromium',
    ]
    for name in ['google-chrome', 'chromium', 'chromium-browser', 'chrome']:
        found = shutil.which(name)
        if found:
            candidates.append(found)
    for item in candidates:
        if not item:
            continue
        if os.path.isabs(item) and Path(item).exists():
            return item
        if not os.path.isabs(item):
            found = shutil.which(item)
            if found:
                return found
    return None


def run_pdf_command(binary: str, html_path: Path, pdf_path: Path, headless_flag: str) -> subprocess.CompletedProcess[str]:
    command = [
        binary,
        headless_flag,
        '--disable-gpu',
        '--no-sandbox',
        '--print-to-pdf-no-header',
        f'--print-to-pdf={pdf_path}',
        html_path.resolve().as_uri(),
    ]
    return subprocess.run(command, capture_output=True, text=True, check=False)


def build_pdf(html_path: Path, pdf_path: Path) -> dict[str, str | bool]:
    binary = chrome_binary()
    if not binary:
        return {'ok': False, 'error': 'Chrome or Chromium was not found. Set CHROME_BIN or install a supported browser.'}
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    last_output = ''
    for flag in ['--headless=new', '--headless']:
        result = run_pdf_command(binary, html_path, pdf_path, flag)
        last_output = (result.stdout or '') + (result.stderr or '')
        if result.returncode == 0 and pdf_path.exists():
            return {'ok': True, 'binary': binary}
    return {'ok': False, 'error': last_output.strip() or 'Chrome failed to render the PDF.', 'binary': binary}


def main() -> int:
    parser = argparse.ArgumentParser(description='Render Markdown submission source into HTML and PDF.')
    parser.add_argument('--input', default='docs/submissions/proposal.md', help='Markdown source file')
    parser.add_argument('--design', default='.codex-loop/design/DESIGN.md', help='Design contract file')
    parser.add_argument('--html-output', default='output/html/proposal.html', help='Rendered HTML output path')
    parser.add_argument('--pdf-output', default='output/pdf/proposal.pdf', help='Rendered PDF output path')
    parser.add_argument('--html-only', action='store_true', help='Skip PDF generation')
    parser.add_argument('--no-pdf', action='store_true', help='Skip PDF generation')
    args = parser.parse_args()

    root = project_root()
    input_path = (root / args.input).resolve()
    design_path = (root / args.design).resolve()
    html_output = (root / args.html_output).resolve()
    pdf_output = (root / args.pdf_output).resolve()

    if not input_path.exists():
        raise FileNotFoundError(input_path)

    markdown_text = read_text(input_path)
    design_text = read_text(design_path)
    preset = extract_preset(design_text)
    reference_pack = extract_reference_pack(design_text)
    title = extract_title(markdown_text)
    body_html = markdown_to_html(markdown_text)
    html_doc = build_html_document(title, body_html, preset, reference_pack)
    write_text(html_output, html_doc)
    print(f'Wrote rendered HTML to {html_output}')

    if args.html_only or args.no_pdf:
        return 0

    result = build_pdf(html_output, pdf_output)
    if not result.get('ok'):
        print(result.get('error', 'Failed to build PDF.'))
        return 2
    print(f'Wrote rendered PDF to {pdf_output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
