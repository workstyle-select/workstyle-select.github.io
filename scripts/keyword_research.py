#!/usr/bin/env python3
"""
無料キーワードリサーチ
- Google Autocomplete API（無料・非公式）
- Related searches
- People Also Ask パターン
有料APIゼロで実装
"""

import json
import time
import yaml
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config" / "settings.yaml"
KEYWORDS_PATH = ROOT / "config" / "keywords.yaml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9",
}


def google_autocomplete(query: str, lang: str = "ja", country: str = "JP") -> list[str]:
    """Google Suggest APIから候補キーワードを取得（無料）"""
    encoded_q = urllib.parse.quote(query, safe="", encoding="utf-8")
    url = (
        f"https://suggestqueries.google.com/complete/search"
        f"?client=firefox&q={encoded_q}&hl={lang}&gl={country}"
    )
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data[1] if len(data) > 1 else []
    except Exception as e:
        print(f"[WARN] Autocomplete failed for '{query}': {e}")
        return []


def expand_keyword(seed: str) -> list[str]:
    """種キーワードから複数のロングテールを展開"""
    results = set()

    # 基本サジェスト
    for kw in google_autocomplete(seed):
        results.add(kw)
    time.sleep(1.5)

    # アルファベット展開（a-z）
    alphabet_prefixes = ["a", "b", "c", "は", "に", "と", "の", "が", "で", "も"]
    for ch in alphabet_prefixes[:5]:
        for kw in google_autocomplete(f"{seed} {ch}"):
            results.add(kw)
        time.sleep(1)

    # 質問形式
    question_prefixes = ["どれ", "なぜ", "いつ", "どこ", "how", "why", "best", "おすすめ", "比較"]
    for prefix in question_prefixes[:4]:
        for kw in google_autocomplete(f"{prefix} {seed}"):
            results.add(kw)
        time.sleep(1)

    return sorted(results)


def estimate_competition(keyword: str) -> str:
    """キーワードの競合推定（文字数と修飾語から簡易判定）"""
    word_count = len(keyword.split())
    has_long_tail_markers = any(m in keyword for m in ["おすすめ", "比較", "レビュー", "ランキング", "方法", "やり方", "とは"])

    if word_count >= 4 or has_long_tail_markers:
        return "low"
    elif word_count >= 2:
        return "medium"
    return "high"


def research_niche(niche_name: str, seeds: list[str], delay: float = 2.0) -> list[dict]:
    """1ニッチ全体のキーワードリサーチ"""
    all_keywords = []
    seen = set()

    for seed in seeds:
        print(f"  [+] Expanding: {seed}")
        expanded = expand_keyword(seed)
        for kw in expanded:
            if kw not in seen and len(kw) > 4:
                seen.add(kw)
                all_keywords.append({
                    "keyword": kw,
                    "niche": niche_name,
                    "competition": estimate_competition(kw),
                    "seed": seed,
                    "discovered_at": datetime.now().isoformat(),
                })
        time.sleep(delay)

    # 低競合を優先ソート
    competition_order = {"low": 0, "medium": 1, "high": 2}
    all_keywords.sort(key=lambda k: competition_order[k["competition"]])
    return all_keywords


def save_to_db(keywords: list[dict]):
    """発見したキーワードをDBに保存"""
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    import db

    db.init_db()
    added = 0
    for kw_data in keywords:
        priority = {"low": 2, "medium": 5, "high": 8}[kw_data["competition"]]
        db.add_keyword(kw_data["keyword"], kw_data["niche"], priority)
        added += 1
    print(f"[DB] Saved {added} keywords")


def run():
    keywords_config = yaml.safe_load(KEYWORDS_PATH.read_text())
    niches = keywords_config.get("niches", {})

    all_found = []
    for niche_key, niche_data in niches.items():
        seeds = niche_data.get("seed_keywords", [])
        if not seeds:
            continue
        print(f"\n[RESEARCH] Niche: {niche_data['name']} ({len(seeds)} seeds)")
        found = research_niche(niche_key, seeds)
        all_found.extend(found)
        print(f"  => Found {len(found)} keywords")

    print(f"\n[TOTAL] {len(all_found)} keywords discovered")
    save_to_db(all_found)

    # 上位30件をプレビュー
    print("\n=== TOP LOW-COMPETITION KEYWORDS ===")
    low_comp = [k for k in all_found if k["competition"] == "low"][:30]
    for i, kw in enumerate(low_comp, 1):
        print(f"{i:2d}. {kw['keyword']} [{kw['niche']}]")

    return all_found


if __name__ == "__main__":
    run()
