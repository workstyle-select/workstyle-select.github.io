#!/usr/bin/env python3
"""
静的サイトジェネレーター
Jinja2テンプレートからHTMLを生成
GitHub Pagesに無料デプロイ
"""

import re
import sys
import yaml
import json
import shutil
from pathlib import Path
from datetime import datetime

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:
    print("[ERROR] pip install jinja2 が必要です")
    sys.exit(1)

ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = ROOT / "templates"
CONTENT_DIR = ROOT / "content" / "articles"
SITE_DIR = ROOT / "site"
CONFIG_PATH = ROOT / "config" / "settings.yaml"


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text())


def parse_frontmatter(content: str) -> tuple[dict, str]:
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    try:
        fm = yaml.safe_load(parts[1]) or {}
        return fm, parts[2]
    except yaml.YAMLError:
        return {}, content


def parse_table(table_lines: list[str]) -> str:
    """Markdownテーブルをhtml <table>に変換"""
    rows = []
    for line in table_lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)

    if len(rows) < 2:
        return "\n".join(f"<p>{inline_md(l)}</p>" for l in table_lines)

    # 2行目はセパレーター（|---|---| の行）なのでスキップ
    header_cells = rows[0]
    body_rows = rows[2:]

    html = '<table>\n<thead>\n<tr>'
    for cell in header_cells:
        html += f'<th>{inline_md(cell)}</th>'
    html += '</tr>\n</thead>\n<tbody>\n'
    for row in body_rows:
        html += '<tr>'
        for cell in row:
            html += f'<td>{inline_md(cell)}</td>'
        html += '</tr>\n'
    html += '</tbody>\n</table>'
    return html


def markdown_to_html(md: str) -> str:
    """軽量なMarkdown→HTML変換（外部ライブラリ不要）"""
    lines = md.split("\n")
    html_lines = []
    in_list = False
    in_code = False
    in_blockquote = False
    table_buffer = []

    def flush_table():
        if table_buffer:
            html_lines.append(parse_table(table_buffer[:]))
            table_buffer.clear()

    for line in lines:
        # コードブロック
        if line.startswith("```"):
            flush_table()
            if in_code:
                html_lines.append("</code></pre>")
                in_code = False
            else:
                lang = line[3:].strip()
                html_lines.append(f'<pre><code class="language-{lang}">')
                in_code = True
            continue
        if in_code:
            html_lines.append(line)
            continue

        # テーブル行（| で始まる行）
        if line.strip().startswith("|"):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            table_buffer.append(line)
            continue
        elif table_buffer:
            flush_table()

        # 見出し
        h_match = re.match(r'^(#{1,6})\s+(.+)', line)
        if h_match:
            level = len(h_match.group(1))
            text = h_match.group(2)
            anchor = re.sub(r'[^\w\s-]', '', text).strip().replace(' ', '-').lower()
            html_lines.append(f'<h{level} id="{anchor}">{text}</h{level}>')
            continue

        # リスト
        if re.match(r'^[-*]\s+', line):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            item = re.sub(r'^[-*]\s+', '', line)
            html_lines.append(f"  <li>{inline_md(item)}</li>")
            continue
        elif in_list and line.strip() == "":
            html_lines.append("</ul>")
            in_list = False

        # 番号付きリスト
        if re.match(r'^\d+\.\s+', line):
            item = re.sub(r'^\d+\.\s+', '', line)
            html_lines.append(f"<li>{inline_md(item)}</li>")
            continue

        # 水平線
        if re.match(r'^---+$', line):
            html_lines.append("<hr>")
            continue

        # 空行
        if line.strip() == "":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("")
            continue

        # コメント（アフィリエイトプレースホルダー含む）
        if line.strip().startswith("<!--") and line.strip().endswith("-->"):
            # DIV/HTMLコンテンツとしてそのまま通過
            inner = line.strip()[4:-3].strip()
            if inner.startswith("<"):
                html_lines.append(inner)
            else:
                html_lines.append(line)
            continue

        # 通常段落
        if line.strip().startswith("<"):
            html_lines.append(line)
            continue

        # 通常段落
        if line.strip():
            html_lines.append(f"<p>{inline_md(line)}</p>")

    flush_table()
    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def inline_md(text: str) -> str:
    """インラインMarkdown変換"""
    # リンク
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    # 太字
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # 斜体
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # コード
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    return text


def load_articles(status_filter: str = "published") -> list[dict]:
    """publishedな記事を全て読み込む"""
    articles = []
    for md_file in sorted(CONTENT_DIR.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)
        if status_filter and fm.get("status", "draft") != status_filter:
            continue
        if not fm.get("word_count"):
            plain_body = re.sub(r'```.*?```', '', body, flags=re.S)
            plain_body = re.sub(r'[#*_`\[\]()<>|:-]', '', plain_body)
            fm["word_count"] = len(re.sub(r'\s+', '', plain_body))
        fm["body_html"] = markdown_to_html(body)
        fm["slug"] = fm.get("slug", md_file.stem)
        articles.append(fm)

    articles.sort(key=lambda a: a.get("updated", a.get("created", "")), reverse=True)
    return articles


def build_site():
    """サイト全体をビルド"""
    config = load_config()
    site_config = config["site"]

    SITE_DIR.mkdir(parents=True, exist_ok=True)

    # Jinja2環境セットアップ
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
    )
    env.globals["site"] = site_config
    env.globals["now"] = datetime.now()

    articles = load_articles(status_filter="published")
    print(f"[BUILD] {len(articles)} published articles found")

    # 各記事ページをビルド
    article_tmpl = env.get_template("article.html")
    for article in articles:
        slug = article["slug"]
        out_dir = SITE_DIR / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        html = article_tmpl.render(article=article, articles=articles)
        (out_dir / "index.html").write_text(html, encoding="utf-8")
        print(f"  [+] /{slug}/")

    # トップページ
    index_tmpl = env.get_template("index.html")
    html = index_tmpl.render(articles=articles[:12])
    (SITE_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"  [+] / (index)")

    # カテゴリページ
    niches = {}
    for a in articles:
        niche = a.get("niche", "other")
        niches.setdefault(niche, []).append(a)

    category_tmpl = env.get_template("category.html")
    for niche, niche_articles in niches.items():
        out_dir = SITE_DIR / "category" / niche
        out_dir.mkdir(parents=True, exist_ok=True)
        html = category_tmpl.render(niche=niche, articles=niche_articles)
        (out_dir / "index.html").write_text(html, encoding="utf-8")
        print(f"  [+] /category/{niche}/")

    # サイトマップ生成
    build_sitemap(articles, site_config["domain"])

    # RSS Feed生成
    build_rss(articles, site_config)

    # 静的アセットをコピー
    static_src = ROOT / "templates" / "static"
    if static_src.exists():
        static_dst = SITE_DIR / "static"
        if static_dst.exists():
            shutil.rmtree(static_dst)
        shutil.copytree(static_src, static_dst)
        print(f"  [+] /static/ (assets)")

    print(f"\n[BUILD] Complete! Site at: {SITE_DIR}")
    return len(articles)


def build_sitemap(articles: list[dict], domain: str):
    """XML サイトマップを生成"""
    urls = [f"https://{domain}/"]
    for a in articles:
        urls.append(f"https://{domain}/{a['slug']}/")

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        xml += f"  <url>\n    <loc>{url}</loc>\n    <changefreq>weekly</changefreq>\n  </url>\n"
    xml += "</urlset>"

    (SITE_DIR / "sitemap.xml").write_text(xml, encoding="utf-8")
    print(f"  [+] /sitemap.xml ({len(urls)} URLs)")


def build_rss(articles: list[dict], site_config: dict):
    """RSS 2.0フィードを生成"""
    domain = site_config["domain"]
    site_name = site_config["name"]
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{site_name}</title>
    <link>https://{domain}/</link>
    <description>{site_config['description']}</description>
    <language>ja</language>
"""
    for a in articles[:20]:
        rss += f"""    <item>
      <title>{a.get('title', '')}</title>
      <link>https://{domain}/{a['slug']}/</link>
      <description>{a.get('description', '')}</description>
      <pubDate>{a.get('updated', a.get('created', ''))}</pubDate>
      <guid>https://{domain}/{a['slug']}/</guid>
    </item>
"""
    rss += "  </channel>\n</rss>"
    (SITE_DIR / "feed.xml").write_text(rss, encoding="utf-8")
    print(f"  [+] /feed.xml")


if __name__ == "__main__":
    n = build_site()
    print(f"\n[DONE] {n} pages built")
