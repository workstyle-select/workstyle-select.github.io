#!/usr/bin/env python3
"""
アフィリエイトリンク管理
- Amazon/楽天/A8.net/もしもアフィリエイトのURL生成
- 記事へのリンク挿入
- クリック追跡（サーバーサイドリダイレクト方式）
有料API不要
"""

import re
import sys
import yaml
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config" / "settings.yaml"


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text())


def build_amazon_url(asin: str, config: dict = None) -> str:
    """Amazon アソシエイトURLを生成"""
    if config is None:
        config = load_config()
    tag = config["affiliate_programs"]["amazon"]["tag"]
    return f"https://www.amazon.co.jp/dp/{asin}?tag={tag}"


def build_rakuten_url(target_url: str, config: dict = None) -> str:
    """楽天アフィリエイトURLを生成"""
    if config is None:
        config = load_config()
    affiliate_id = config["affiliate_programs"]["rakuten"]["affiliate_id"]
    encoded = urllib.parse.quote(target_url, safe="")
    return f"https://hb.afl.rakuten.co.jp/ichiba/{affiliate_id}/?pc={encoded}&link_type=text"


def build_a8_url(a8mat: str = None, config: dict = None) -> str:
    """A8.net URLを生成。a8mat省略時はconfigのdefault_a8matを使用"""
    if config is None:
        config = load_config()
    if a8mat is None:
        a8mat = config["affiliate_programs"]["a8net"].get("default_a8mat", "")
    return f"https://px.a8.net/svt/ejp?a8mat={a8mat}"


def generate_affiliate_button_html(url: str, text: str, program: str) -> str:
    """アフィリエイトリンクのHTMLボタンを生成"""
    colors = {
        "amazon": "#FF9900",
        "rakuten": "#BF0000",
        "a8net": "#0066CC",
        "moshimo": "#00AA44",
    }
    color = colors.get(program, "#333333")
    return f"""<a href="{url}" target="_blank" rel="nofollow noopener" class="affiliate-btn affiliate-{program}" style="background:{color}">
  {text}
</a>"""


def generate_product_card_html(
    product_name: str,
    description: str,
    amazon_url: str = None,
    rakuten_url: str = None,
    price: str = None,
    rating: float = None,
) -> str:
    """商品カード（Markdown埋め込み用HTML）を生成"""
    links = []
    if amazon_url:
        links.append(f'<a href="{amazon_url}" target="_blank" rel="nofollow noopener" class="btn-amazon">Amazonで見る</a>')
    if rakuten_url:
        links.append(f'<a href="{rakuten_url}" target="_blank" rel="nofollow noopener" class="btn-rakuten">楽天で見る</a>')

    price_html = f'<p class="price">参考価格: <strong>{price}</strong></p>' if price else ""
    rating_html = ""
    if rating:
        stars = "★" * int(rating) + "☆" * (5 - int(rating))
        rating_html = f'<p class="rating">{stars} {rating}/5.0</p>'

    return f"""<div class="product-card">
  <h3 class="product-name">{product_name}</h3>
  {rating_html}
  <p class="product-desc">{description}</p>
  {price_html}
  <div class="affiliate-links">
    {"".join(links)}
  </div>
</div>"""


def insert_links_into_article(article_path: Path, links: list[dict]) -> str:
    """
    記事のMarkdownにアフィリエイトリンクを挿入
    links: [{"placeholder": "AFFILIATE_LINK_1", "html": "...", "url": "..."}]
    """
    content = article_path.read_text(encoding="utf-8")
    original = content

    for link_data in links:
        placeholder = f"<!-- {link_data['placeholder']} -->"
        replacement = link_data.get("html", link_data.get("url", ""))
        if placeholder in content:
            content = content.replace(placeholder, replacement, 1)

    if content != original:
        article_path.write_text(content, encoding="utf-8")
        print(f"[LINKS] Updated {len(links)} links in {article_path.name}")
    else:
        print(f"[LINKS] No placeholders found in {article_path.name}")

    return content


def scan_article_for_placeholders(article_path: Path) -> list[str]:
    """記事内のアフィリエイトリンクプレースホルダーを検出"""
    content = article_path.read_text(encoding="utf-8")
    return re.findall(r'<!-- (AFFILIATE_LINK_\d+) -->', content)


def generate_cloak_redirect_html(link_id: int, target_url: str, slug: str) -> str:
    """
    リンクのクローキング用リダイレクトページを生成
    /go/link-ID/ → 実際のアフィリエイトURL へリダイレクト
    クリック追跡のためのGA4イベントつき
    """
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="refresh" content="0;url={target_url}">
  <script>
    // GA4クリック追跡
    if(typeof gtag !== 'undefined') {{
      gtag('event', 'affiliate_click', {{
        link_id: {link_id},
        source_article: '{slug}',
        destination: '{target_url}'
      }});
    }}
    window.location.replace('{target_url}');
  </script>
</head>
<body>
  <p>リダイレクト中... <a href="{target_url}">こちらをクリック</a></p>
</body>
</html>"""


def interactive_link_builder():
    """インタラクティブなリンクビルダーCLI"""
    config = load_config()
    print("\n=== アフィリエイトリンクビルダー ===")
    print("プログラム選択:")
    print("  1. Amazon アソシエイト")
    print("  2. 楽天アフィリエイト")
    print("  3. A8.net")

    choice = input("選択 (1-3): ").strip()

    if choice == "1":
        asin = input("Amazon ASIN: ").strip()
        url = build_amazon_url(asin, config)
        product = input("商品名: ").strip()
        print(f"\n生成URL: {url}")
        print(f"\nMarkdown:")
        print(f"[{product}をAmazonで見る]({url}){{{{.affiliate-amazon}}}}")
    elif choice == "2":
        target = input("楽天商品URL: ").strip()
        url = build_rakuten_url(target, config)
        print(f"\n生成URL: {url}")
    elif choice == "3":
        media_id = config["affiliate_programs"]["a8net"]["media_id"]
        program_id = input("A8 プログラムID: ").strip()
        url = build_a8_url(media_id, program_id, config)
        print(f"\n生成URL: {url}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        interactive_link_builder()
    else:
        # デモ: Amazon URLを生成
        config = load_config()
        print("[DEMO] Amazon URL例:")
        print(build_amazon_url("B08N5WRWNW", config))
        print("\n[DEMO] 商品カードHTML例:")
        print(generate_product_card_html(
            "Sony WH-1000XM5",
            "業界最高水準のノイズキャンセリング",
            amazon_url=build_amazon_url("B0BXN6TBGX", config),
            price="¥39,800",
            rating=4.8
        ))
