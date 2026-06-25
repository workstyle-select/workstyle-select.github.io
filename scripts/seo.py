#!/usr/bin/env python3
"""
SEO最適化ツール
- 記事のSEOスコア計算
- メタタグ最適化
- 内部リンク提案
- 構造化データ(JSON-LD)生成
"""

import re
import sys
import yaml
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """MarkdownのFrontmatterをパース"""
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


def count_words_ja(text: str) -> int:
    """日本語テキストの文字数を計算"""
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'#{1,6}\s+', '', clean)
    clean = re.sub(r'\*{1,3}', '', clean)
    clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)
    clean = re.sub(r'<!--.*?-->', '', clean, flags=re.DOTALL)
    clean = re.sub(r'```.*?```', '', clean, flags=re.DOTALL)
    return len(clean.replace('\n', '').replace(' ', ''))


def check_seo(article_path: Path) -> dict:
    """記事のSEOスコアをチェック（0〜100点）"""
    content = article_path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(content)

    issues = []
    score = 100

    keyword = fm.get("keyword", "")
    title = fm.get("title", "")
    description = fm.get("description", "")

    # --- タイトルチェック ---
    if not title:
        issues.append(("ERROR", "タイトルがありません"))
        score -= 20
    elif len(title) > 60:
        issues.append(("WARN", f"タイトルが長すぎます ({len(title)}文字 / 推奨60以内)"))
        score -= 5
    elif keyword and keyword not in title:
        issues.append(("WARN", f"タイトルにキーワード「{keyword}」が含まれていません"))
        score -= 10

    # --- メタディスクリプションチェック ---
    if not description:
        issues.append(("WARN", "メタディスクリプションがありません"))
        score -= 10
    elif len(description) > 160:
        issues.append(("WARN", f"ディスクリプションが長すぎます ({len(description)}文字 / 推奨160以内)"))
        score -= 3
    elif len(description) < 50:
        issues.append(("WARN", f"ディスクリプションが短すぎます ({len(description)}文字)"))
        score -= 5

    # --- 文字数チェック ---
    word_count = count_words_ja(body)
    if word_count < 1000:
        issues.append(("ERROR", f"文字数が少なすぎます ({word_count}字 / 推奨2000字以上)"))
        score -= 20
    elif word_count < 2000:
        issues.append(("WARN", f"文字数をもう少し増やしてください ({word_count}字)"))
        score -= 5
    else:
        issues.append(("OK", f"文字数: {word_count}字 ✓"))

    # --- 見出しチェック ---
    h2_count = len(re.findall(r'^## .+', body, re.MULTILINE))
    h3_count = len(re.findall(r'^### .+', body, re.MULTILINE))
    if h2_count < 3:
        issues.append(("WARN", f"H2見出しが少ない ({h2_count}個 / 推奨3個以上)"))
        score -= 8
    else:
        issues.append(("OK", f"H2: {h2_count}個, H3: {h3_count}個 ✓"))

    # --- キーワード密度チェック ---
    if keyword:
        kw_count = body.lower().count(keyword.lower())
        density = (kw_count / max(word_count, 1)) * 100
        if kw_count == 0:
            issues.append(("WARN", f"キーワード「{keyword}」が本文に含まれていません"))
            score -= 15
        elif density > 3:
            issues.append(("WARN", f"キーワード密度が高すぎます ({density:.1f}%) - スパムと判定される可能性"))
            score -= 8
        else:
            issues.append(("OK", f"キーワード密度: {density:.1f}% ({kw_count}回) ✓"))

    # --- 画像ALTテキストチェック ---
    img_no_alt = len(re.findall(r'!\[\]', body))
    if img_no_alt > 0:
        issues.append(("WARN", f"ALTテキストなしの画像: {img_no_alt}個"))
        score -= img_no_alt * 2

    # --- リンクチェック ---
    internal_links = len(re.findall(r'\[.+?\]\(/[^)]+\)', body))
    affiliate_links = len(re.findall(r'<!-- AFFILIATE_LINK', body))
    filled_affiliate = len(re.findall(r'\[.+?\]\(https?://[^)]+\)', body))
    issues.append(("INFO", f"内部リンク: {internal_links}個 / アフィリエイトリンク: {filled_affiliate}個"))

    score = max(0, min(100, score))

    return {
        "score": score,
        "word_count": word_count,
        "keyword": keyword,
        "title": title,
        "issues": issues,
        "h2_count": h2_count,
        "internal_links": internal_links,
        "affiliate_links": filled_affiliate,
    }


def generate_meta_tags(fm: dict, site_url: str) -> str:
    """OGP/TwitterカードなどのHTMLメタタグを生成"""
    title = fm.get("title", "")
    description = fm.get("description", "")
    slug = fm.get("slug", "")
    url = f"{site_url}/{slug}/"

    return f"""  <!-- SEO -->
  <meta name="description" content="{description}">
  <link rel="canonical" href="{url}">

  <!-- OGP -->
  <meta property="og:type" content="article">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:url" content="{url}">

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{description}">"""


def generate_json_ld(fm: dict, site_name: str, site_url: str) -> str:
    """レビュー記事用のJSON-LD構造化データを生成"""
    title = fm.get("title", "")
    description = fm.get("description", "")
    slug = fm.get("slug", "")
    created = fm.get("created", "")
    updated = fm.get("updated", created)

    return f"""<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{title}",
  "description": "{description}",
  "author": {{
    "@type": "Organization",
    "name": "{site_name}"
  }},
  "publisher": {{
    "@type": "Organization",
    "name": "{site_name}",
    "url": "{site_url}"
  }},
  "datePublished": "{created}",
  "dateModified": "{updated}",
  "url": "{site_url}/{slug}/"
}}
</script>"""


def generate_faq_json_ld(faqs: list[tuple[str, str]]) -> str:
    """FAQ用の構造化データを生成"""
    entries = []
    for q, a in faqs:
        entries.append(f'''    {{
      "@type": "Question",
      "name": "{q}",
      "acceptedAnswer": {{
        "@type": "Answer",
        "text": "{a}"
      }}
    }}''')

    return f"""<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
{",".join(entries)}
  ]
}}
</script>"""


def extract_faqs(body: str) -> list[tuple[str, str]]:
    """記事のFAQセクションから質問・回答を抽出"""
    faqs = []
    pattern = re.compile(r'### Q: (.+?)\n\*\*A:\*\* (.+?)(?=\n### Q:|\Z)', re.DOTALL)
    for match in pattern.finditer(body):
        q = match.group(1).strip()
        a = match.group(2).strip()
        faqs.append((q, a))
    return faqs


def suggest_internal_links(current_slug: str, all_articles: list[dict]) -> list[dict]:
    """内部リンク候補を提案"""
    suggestions = []
    for article in all_articles:
        if article.get("slug") == current_slug:
            continue
        if article.get("status") == "published":
            suggestions.append({
                "title": article["title"],
                "slug": article["slug"],
                "url": f"/{article['slug']}/",
            })
    return suggestions[:5]


def print_seo_report(result: dict):
    """SEOチェック結果をコンソールに表示"""
    score = result["score"]
    score_color = "OK" if score >= 80 else ("WARN" if score >= 60 else "ERROR")

    print(f"\n{'='*60}")
    print(f"SEO スコア: {score}/100 [{score_color}]")
    print(f"{'='*60}")
    print(f"文字数: {result['word_count']:,}字")
    print(f"キーワード: {result['keyword']}")
    print(f"H2見出し: {result['h2_count']}個")
    print(f"内部リンク: {result['internal_links']}個")
    print(f"{'='*60}")
    print("Issues:")
    for level, msg in result["issues"]:
        icon = {"OK": "✓", "WARN": "⚠", "ERROR": "✗", "INFO": "i"}.get(level, "·")
        print(f"  [{level:5s}] {icon} {msg}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("slug", help="チェックする記事のslug")
    args = parser.parse_args()

    article_path = ROOT / "content" / "articles" / f"{args.slug}.md"
    if not article_path.exists():
        print(f"[ERROR] 記事が見つかりません: {article_path}")
        sys.exit(1)

    result = check_seo(article_path)
    print_seo_report(result)
