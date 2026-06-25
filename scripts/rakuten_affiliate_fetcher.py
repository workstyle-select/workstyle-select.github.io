#!/usr/bin/env python3
"""Fetch Rakuten product data and inject visual affiliate cards into articles."""

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config" / "settings.yaml"

EXCLUDE_WORDS = (
    "カバー",
    "ケースカバー",
    "バンド",
    "ベルト",
    "フィルム",
    "保護",
    "充電器",
    "充電ケーブル",
    "スタンド",
    "ストラップ",
    "中古",
    "未使用品",
)


@dataclass
class ProductQuery:
    rank: int
    name: str
    rating: str
    price_hint: int | None


@dataclass
class RakutenProduct:
    name: str
    url: str
    image: str
    price: int | None
    rating: float | None
    review_count: int | None


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def build_rakuten_affiliate_url(target_url: str, config: dict) -> str:
    affiliate_id = config["affiliate_programs"]["rakuten"]["affiliate_id"]
    encoded = urllib.parse.quote(target_url, safe="")
    return f"https://hb.afl.rakuten.co.jp/ichiba/{affiliate_id}/?pc={encoded}&link_type=text"


def search_url(query: str) -> str:
    quoted = urllib.parse.quote_plus(query)
    return f"https://search.rakuten.co.jp/search/mall/{quoted}/"


def fetch_html(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "Chrome/120.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def extract_js_string(source: str, key: str) -> str | None:
    marker = f'"{key}":"'
    start = source.find(marker)
    if start == -1:
        return None
    i = start + len(marker)
    escaped = False
    chars: list[str] = []
    while i < len(source):
        char = source[i]
        if escaped:
            chars.append("\\" + char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            break
        else:
            chars.append(char)
        i += 1
    try:
        return json.loads('"' + "".join(chars) + '"')
    except json.JSONDecodeError:
        return None


def parse_products(search_html: str) -> list[RakutenProduct]:
    carousel = extract_js_string(search_html, "structuredDataCarousel")
    if not carousel:
        return []
    try:
        data = json.loads(carousel)
    except json.JSONDecodeError:
        return []

    products: list[RakutenProduct] = []
    for element in data.get("itemListElement", []):
        item = element.get("item", {})
        offers = item.get("offers", {})
        rating = item.get("aggregateRating", {})
        images = item.get("image") or []
        image = images[0] if images else ""
        products.append(
            RakutenProduct(
                name=item.get("name", ""),
                url=item.get("url", ""),
                image=image,
                price=offers.get("price"),
                rating=rating.get("ratingValue"),
                review_count=rating.get("reviewCount"),
            )
        )
    return [p for p in products if p.name and p.url and p.image]


def product_tokens(name: str) -> list[str]:
    tokens = re.split(r"[\s　+・/（）()]+", name)
    return [t.lower() for t in tokens if t]


def model_tokens(name: str) -> list[str]:
    tokens = product_tokens(name)
    return [
        token
        for token in tokens
        if re.search(r"\d", token) or token in {"se", "pro", "ultra", "s"}
    ]


def score_product(product: RakutenProduct, query: ProductQuery) -> int:
    haystack = product.name.lower()
    score = 0
    for token in product_tokens(query.name):
        if token in haystack:
            score += 14
        elif token in model_tokens(query.name):
            score -= 35
    for token in model_tokens(query.name):
        if token in haystack:
            score += 24
    if any(word.lower() in haystack for word in EXCLUDE_WORDS):
        score -= 55
    if query.price_hint and product.price:
        if product.price >= max(8000, int(query.price_hint * 0.45)):
            score += 18
        else:
            score -= 18
    if product.rating:
        score += int(float(product.rating) * 2)
    if product.review_count:
        score += min(int(product.review_count) // 100, 8)
    return score


def find_best_product(query: ProductQuery) -> RakutenProduct | None:
    search_terms = [
        f"{query.name} 本体",
        query.name,
    ]
    candidates: list[RakutenProduct] = []
    for term in search_terms:
        page = fetch_html(search_url(term))
        candidates.extend(parse_products(page))
        if candidates:
            break
    if not candidates:
        return None
    best = max(candidates, key=lambda product: score_product(product, query))
    if score_product(best, query) < 25:
        return None
    return best


def extract_price_hint(section: str) -> int | None:
    match = re.search(r"価格帯[：:]\s*[¥￥]?([0-9,]+)", section)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def extract_product_queries(markdown: str) -> list[ProductQuery]:
    heading_pattern = re.compile(r"^###\s*(\d+)位[：:]\s*(.+?)（おすすめ度([★☆]+)）", re.M)
    matches = list(heading_pattern.finditer(markdown))
    queries: list[ProductQuery] = []
    for index, match in enumerate(matches):
        section_start = match.end()
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        section = markdown[section_start:section_end]
        queries.append(
            ProductQuery(
                rank=int(match.group(1)),
                name=match.group(2).strip(),
                rating=match.group(3),
                price_hint=extract_price_hint(section),
            )
        )
    return queries


def find_balanced_div_end(text: str, start: int) -> int | None:
    pattern = re.compile(r"</?div\b[^>]*>", re.I)
    depth = 0
    for match in pattern.finditer(text, start):
        tag = match.group(0)
        if tag.startswith("</"):
            depth -= 1
            if depth == 0:
                return match.end()
        else:
            depth += 1
    return None


def generate_card(query: ProductQuery, product: RakutenProduct, config: dict) -> str:
    affiliate_url = build_rakuten_affiliate_url(product.url, config)
    price = f"¥{product.price:,}" if product.price else "価格を確認"
    rating_html = ""
    if product.rating:
        reviews = f" / {product.review_count:,}件" if product.review_count else ""
        rating_html = f'<span class="product-rating">★ {float(product.rating):.2f}{reviews}</span>'

    return f"""<div class="product-card product-card--media">
  <a class="product-image-link" href="{html.escape(affiliate_url)}" target="_blank" rel="nofollow noopener">
    <img src="{html.escape(product.image)}" alt="{html.escape(query.name)}の商品画像" class="product-image" loading="lazy">
  </a>
  <div class="product-content">
    <p class="product-rank">{query.rank}位 / おすすめ度{query.rating}</p>
    <h3 class="product-name">{html.escape(query.name)}</h3>
    <p class="product-desc">{html.escape(product.name)}</p>
    <div class="product-meta">
      <span class="price">楽天価格: <strong>{price}</strong></span>
      {rating_html}
    </div>
    <div class="affiliate-links">
      <a href="{html.escape(affiliate_url)}" target="_blank" rel="nofollow noopener" class="btn-rakuten">楽天で商品画像つき詳細を見る</a>
    </div>
  </div>
</div>"""


def replace_or_insert_card(markdown: str, query: ProductQuery, card_html: str) -> str:
    heading = re.search(
        rf"^###\s*{query.rank}位[：:].*?$",
        markdown,
        flags=re.M,
    )
    if not heading:
        return markdown

    next_heading = re.search(r"^###\s*\d+位[：:]", markdown[heading.end():], flags=re.M)
    section_end = heading.end() + next_heading.start() if next_heading else len(markdown)
    section = markdown[heading.end():section_end]

    card_match = re.search(r'<div class="product-card[^"]*">', section)
    if card_match:
        absolute_start = heading.end() + card_match.start()
        absolute_end = find_balanced_div_end(markdown, absolute_start)
        if absolute_end:
            return markdown[:absolute_start] + card_html + markdown[absolute_end:]

    separator = section.rfind("\n---")
    insert_at = heading.end() + separator if separator != -1 else section_end
    return markdown[:insert_at].rstrip() + "\n\n" + card_html + "\n\n" + markdown[insert_at:].lstrip()


def update_article(article_path: Path) -> None:
    config = load_config()
    markdown = article_path.read_text(encoding="utf-8")
    queries = extract_product_queries(markdown)
    if not queries:
        print(f"[ERROR] 商品ランキング見出しが見つかりません: {article_path}")
        sys.exit(1)

    updated = markdown
    for query in queries:
        product = find_best_product(query)
        if not product:
            print(f"[WARN] 商品が見つかりません: {query.name}")
            continue
        card = generate_card(query, product, config)
        updated = replace_or_insert_card(updated, query, card)
        print(f"[RAKUTEN] {query.name} -> {product.name[:60]}...")

    article_path.write_text(updated, encoding="utf-8")
    print(f"[UPDATED] {article_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="楽天検索から商品画像つきアフィリエイトカードを挿入")
    parser.add_argument("article", type=Path, help="更新する記事Markdown")
    args = parser.parse_args()
    update_article(args.article)


if __name__ == "__main__":
    main()
