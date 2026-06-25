#!/usr/bin/env python3
"""
楽天 Item Search API で商品画像を取得し、全記事の product-card を
画像付きレイアウト（.product-card--media）に書き換える。

使い方:
  python3 scripts/rakuten_image_linker.py
  python3 scripts/rakuten_image_linker.py --app-id YOUR_APP_ID
  python3 scripts/rakuten_image_linker.py --dry-run  # 変更せず確認のみ

App ID の取得:
  https://webservice.rakuten.co.jp/ で無料登録して App ID を発行。
  その後 config/settings.yaml の rakuten.app_id に記入するか
  --app-id オプションで渡す。
"""

import re
import os
import sys
import time
import argparse
import urllib.parse
import urllib.request
import json
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES_DIR = os.path.join(BASE_DIR, "content", "articles")
SETTINGS_FILE = os.path.join(BASE_DIR, "config", "settings.yaml")
RAKUTEN_API = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706"
REQUEST_DELAY = 1.0  # API レート制限対策 (秒)


def load_settings():
    with open(SETTINGS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def search_rakuten_item(app_id: str, keyword: str) -> dict | None:
    """楽天 Ichiba で商品を検索し、最初のヒットを返す。"""
    params = urllib.parse.urlencode({
        "applicationId": app_id,
        "keyword": keyword,
        "hits": 1,
        "sort": "+itemPrice",
        "formatVersion": 2,
    })
    url = f"{RAKUTEN_API}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "UltiAffi/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        items = data.get("Items", [])
        if not items:
            return None
        item = items[0]
        return {
            "name": item.get("itemName", ""),
            "price": item.get("itemPrice", 0),
            "url": item.get("itemUrl", ""),
            "image": (item.get("mediumImageUrls") or [{}])[0].get("imageUrl", ""),
        }
    except Exception as e:
        print(f"  [API ERROR] {keyword}: {e}", file=sys.stderr)
        return None


def build_affiliate_url(affiliate_id: str, item_url: str) -> str:
    encoded = urllib.parse.quote(item_url, safe="")
    return (
        f"https://hb.afl.rakuten.co.jp/ichiba/{affiliate_id}/"
        f"?pc={encoded}&link_type=text"
    )


def extract_product_cards(content: str):
    """product-card div の (start, end, inner_html) タプルのリストを返す。"""
    results = []
    i = 0
    while True:
        start = content.find('<div class="product-card"', i)
        if start == -1:
            break
        depth = 0
        pos = start
        while pos < len(content):
            if content[pos:pos+4] == "<div":
                depth += 1
                pos += 4
            elif content[pos:pos+6] == "</div>":
                depth -= 1
                if depth == 0:
                    end = pos + 6
                    inner = content[start:end]
                    results.append((start, end, inner))
                    i = end
                    break
                pos += 6
            else:
                pos += 1
        else:
            break
    return results


def build_image_card(original_html: str, item: dict, affiliate_id: str) -> str:
    """既存の product-card HTML を画像付きレイアウトに変換する。"""
    # <div class="product-card" ...> の style 属性をそのまま引き継ぐ
    style_match = re.search(r'<div class="product-card"([^>]*)>', original_html)
    attrs = style_match.group(1) if style_match else ""

    # 内部コンテンツ（開き div タグと最後の </div> を除いた部分）
    open_tag_end = original_html.index(">") + 1
    inner = original_html[open_tag_end:-6].strip()  # 末尾 </div> を除く

    aff_url = build_affiliate_url(affiliate_id, item["url"])
    img_url = item["image"].replace("_ex=128x128", "_ex=200x200")  # 少し大きめに
    product_name = re.search(r'<h3 class="product-name">(.*?)</h3>', inner)
    alt_text = product_name.group(1) if product_name else item["name"]

    return (
        f'<div class="product-card product-card--media"{attrs}>\n'
        f'  <a href="{aff_url}" target="_blank" rel="nofollow noopener" class="product-image-link">\n'
        f'    <img src="{img_url}" alt="{alt_text}" class="product-image" loading="lazy">\n'
        f'  </a>\n'
        f'  <div class="product-content">\n'
        f'{chr(10).join("    " + line for line in inner.splitlines())}\n'
        f'  </div>\n'
        f'</div>'
    )


def already_has_image(card_html: str) -> bool:
    return 'product-card--media' in card_html or 'product-image' in card_html


def process_article(path: str, app_id: str, affiliate_id: str, dry_run: bool) -> int:
    content = open(path, encoding="utf-8").read()
    cards = extract_product_cards(content)
    if not cards:
        return 0

    # 末尾から置換することでオフセットがずれないようにする
    cards_reversed = list(reversed(cards))
    updated = 0

    for start, end, card_html in cards_reversed:
        if already_has_image(card_html):
            continue

        name_match = re.search(r'<h3 class="product-name">(.*?)</h3>', card_html)
        if not name_match:
            continue
        product_name = name_match.group(1).strip()

        print(f"  検索: {product_name}")
        item = search_rakuten_item(app_id, product_name)
        time.sleep(REQUEST_DELAY)

        if not item or not item["image"]:
            print(f"  → 画像なし、スキップ")
            continue

        print(f"  → {item['name'][:40]} ¥{item['price']:,} {item['image'][:60]}...")
        new_card = build_image_card(card_html, item, affiliate_id)

        if not dry_run:
            content = content[:start] + new_card + content[end:]
        updated += 1

    if updated > 0 and not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return updated


def main():
    parser = argparse.ArgumentParser(description="楽天商品画像を記事に挿入")
    parser.add_argument("--app-id", help="楽天 Web Services Application ID")
    parser.add_argument("--dry-run", action="store_true", help="ファイルを変更せず確認のみ")
    parser.add_argument("--article", help="特定の記事ファイル名のみ処理（例: monitaa-bizinesu-osusume.md）")
    args = parser.parse_args()

    settings = load_settings()
    rakuten = settings["affiliate_programs"]["rakuten"]
    affiliate_id = rakuten["affiliate_id"]
    app_id = args.app_id or rakuten.get("app_id", "")

    if not app_id:
        print("エラー: Rakuten App ID が必要です。")
        print("  1. https://webservice.rakuten.co.jp/ で無料登録")
        print("  2. config/settings.yaml の rakuten.app_id に記入")
        print("  3. または --app-id YOUR_APP_ID を指定して実行")
        sys.exit(1)

    if args.dry_run:
        print("[DRY RUN] ファイルは変更しません\n")

    article_files = (
        [args.article]
        if args.article
        else sorted(f for f in os.listdir(ARTICLES_DIR) if f.endswith(".md"))
    )

    total_updated = 0
    for fname in article_files:
        path = os.path.join(ARTICLES_DIR, fname)
        if not os.path.exists(path):
            print(f"ファイルが見つかりません: {fname}")
            continue
        print(f"\n[{fname}]")
        n = process_article(path, app_id, affiliate_id, args.dry_run)
        print(f"  → {n} 商品を更新")
        total_updated += n

    print(f"\n完了: 合計 {total_updated} 商品カードを{'確認' if args.dry_run else '更新'}しました")


if __name__ == "__main__":
    main()
