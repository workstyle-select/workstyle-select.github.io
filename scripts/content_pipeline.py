#!/usr/bin/env python3
"""
コンテンツ生成パイプライン
Claude Code / Codex CLIと連携してアフィリエイト記事を半自動生成
"""

import os
import sys
import yaml
import json
import subprocess
from pathlib import Path
from datetime import datetime
from slugify import slugify

ROOT = Path(__file__).parent.parent
CONTENT_DIR = ROOT / "content" / "articles"
PROMPTS_DIR = ROOT / "prompts"
CONFIG_PATH = ROOT / "config" / "settings.yaml"


def load_config():
    return yaml.safe_load(CONFIG_PATH.read_text())


def load_prompt(prompt_name: str, **kwargs) -> str:
    """プロンプトテンプレートを読み込んで変数展開"""
    prompt_path = PROMPTS_DIR / f"{prompt_name}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_path}")
    template = prompt_path.read_text(encoding="utf-8")
    for key, value in kwargs.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))
    return template


def generate_article_outline(keyword: str, niche: str) -> str:
    """記事のアウトラインを生成するプロンプトを出力"""
    prompt = load_prompt("article_outline", keyword=keyword, niche=niche)
    print("\n" + "="*60)
    print("CLAUDE/CODEX へのプロンプト (コピーして使用):")
    print("="*60)
    print(prompt)
    print("="*60 + "\n")
    return prompt


def create_article_template(keyword: str, niche: str, title: str = None) -> Path:
    """記事のMarkdownテンプレートを作成"""
    if not title:
        title = f"【{datetime.now().year}年最新】{keyword} - 完全ガイド"

    slug = slugify(keyword, allow_unicode=False)
    if not slug:
        slug = f"article-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    article_path = CONTENT_DIR / f"{slug}.md"
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    if article_path.exists():
        print(f"[WARN] Article already exists: {article_path}")
        return article_path

    config = load_config()
    site_name = config["site"]["name"]

    frontmatter = f"""---
title: "{title}"
keyword: "{keyword}"
niche: "{niche}"
slug: "{slug}"
status: "draft"
created: "{datetime.now().strftime('%Y-%m-%d')}"
updated: "{datetime.now().strftime('%Y-%m-%d')}"
description: ""
tags: []
affiliate_programs: []
seo_score: 0
word_count: 0
---

<!--
  記事テンプレート: {keyword}
  作成日: {datetime.now().strftime('%Y-%m-%d')}
  ニッチ: {niche}

  使い方:
  1. このファイルをエディタで開く
  2. claude コマンドで記事生成:
     $ claude "以下のキーワードで2000字以上のアフィリエイト記事を日本語で書いて: {keyword}"
  3. 生成された内容をここに貼り付ける
  4. make seo-check slug={slug} で SEO確認
  5. make publish でサイトに公開
-->

# {title}

<!-- INTRO: 導入文（150字以内）ここから -->
<!-- INTRO END -->

## 目次

## {keyword}とは？

## {keyword}のおすすめ選び方

## {keyword} ランキングTOP5

### 1位: [商品名]

<!-- AFFILIATE_LINK_1 -->

### 2位: [商品名]

<!-- AFFILIATE_LINK_2 -->

### 3位: [商品名]

<!-- AFFILIATE_LINK_3 -->

## {keyword} よくある質問 (FAQ)

### Q: [質問1]
**A:** [回答1]

### Q: [質問2]
**A:** [回答2]

## まとめ

<!-- CTA: まとめのコール・トゥ・アクション -->

---
*この記事は{site_name}が作成しました。最終更新: {datetime.now().strftime('%Y年%m月%d日')}*
"""

    article_path.write_text(frontmatter, encoding="utf-8")
    print(f"[CREATED] {article_path}")
    return article_path


def generate_claude_command(keyword: str, niche: str, style: str = "review") -> str:
    """Claude Code CLIで記事を生成するコマンドを出力"""
    prompt = load_prompt("article_writer", keyword=keyword, niche=niche, style=style)
    prompt_escaped = prompt.replace('"', '\\"')

    cmd = f'''claude "{prompt_escaped}"'''

    print("\n=== Claude Code コマンド ===")
    print(f"# 記事生成: {keyword}")
    print(f"\n$ {cmd[:200]}...\n")

    # プロンプトをファイルに保存して参照させる
    prompt_file = ROOT / "prompts" / f"_current_{slugify(keyword, allow_unicode=False)}.md"
    prompt_file.write_text(prompt, encoding="utf-8")
    print(f"# または以下でプロンプトファイルから実行:")
    print(f"$ claude < '{prompt_file}'")
    return cmd


def run_with_claude(keyword: str, article_path: Path) -> bool:
    """Claude CLIを実行して記事を生成（インタラクティブモード）"""
    prompt_file = PROMPTS_DIR / "article_writer.md"
    if not prompt_file.exists():
        print("[ERROR] article_writer.md prompt not found")
        return False

    niche_guess = "general"
    print(f"\n[CLAUDE] Generating article for: {keyword}")
    print(f"[CLAUDE] Output: {article_path}")
    print("\n実行するには以下のコマンドを使用:")
    print(f"  $ claude --print 'キーワード「{keyword}」の詳細アフィリエイト記事を書いて' > /tmp/article_draft.md")
    print(f"  $ cat /tmp/article_draft.md >> {article_path}")
    return True


def batch_create(keywords: list[str], niche: str):
    """複数キーワードの記事テンプレートをバッチ作成"""
    created = []
    for kw in keywords:
        path = create_article_template(kw, niche)
        created.append({"keyword": kw, "path": str(path)})
    print(f"\n[BATCH] Created {len(created)} article templates")

    # バッチプロセスリスト出力
    batch_file = ROOT / "content" / "batch_queue.json"
    if batch_file.exists():
        existing = json.loads(batch_file.read_text())
    else:
        existing = []
    existing.extend(created)
    batch_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    return created


def show_workflow():
    """記事生成ワークフローを表示"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║           UltiAffi コンテンツ生成ワークフロー              ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Step 1: キーワードリサーチ                                  ║
║    $ make research                                           ║
║                                                              ║
║  Step 2: 優先キーワード確認                                  ║
║    $ make keywords-todo                                      ║
║                                                              ║
║  Step 3: 記事テンプレート作成                                ║
║    $ make new-article KEYWORD="ワイヤレスイヤホン おすすめ" ║
║                                                              ║
║  Step 4: Claude/Codexで記事生成 [半自動]                    ║
║    $ claude (プロンプトで記事執筆を依頼)                    ║
║    または                                                    ║
║    $ codex (OpenAI Codex CLIで生成)                         ║
║                                                              ║
║  Step 5: SEOチェック＆最適化                                ║
║    $ make seo-check SLUG=article-slug                       ║
║                                                              ║
║  Step 6: アフィリエイトリンク挿入                           ║
║    $ make add-links SLUG=article-slug                       ║
║                                                              ║
║  Step 7: サイトビルド＆公開                                  ║
║    $ make publish                                            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="コンテンツ生成パイプライン")
    parser.add_argument("action", choices=["new", "batch", "workflow", "claude-cmd"])
    parser.add_argument("--keyword", "-k", help="ターゲットキーワード")
    parser.add_argument("--niche", "-n", default="general", help="ニッチ")
    parser.add_argument("--title", "-t", help="記事タイトル")
    args = parser.parse_args()

    if args.action == "workflow":
        show_workflow()
    elif args.action == "new":
        if not args.keyword:
            print("[ERROR] --keyword が必要です")
            sys.exit(1)
        path = create_article_template(args.keyword, args.niche, args.title)
        generate_claude_command(args.keyword, args.niche)
    elif args.action == "claude-cmd":
        if not args.keyword:
            print("[ERROR] --keyword が必要です")
            sys.exit(1)
        generate_claude_command(args.keyword, args.niche)
    elif args.action == "batch":
        # DBから未処理キーワードをバッチ処理
        sys.path.insert(0, str(ROOT / "scripts"))
        import db
        db.init_db()
        keywords_data = db.get_keywords(status="todo", limit=10)
        if not keywords_data:
            print("未処理キーワードがありません。先に `make research` を実行してください")
        else:
            for kw_data in keywords_data[:5]:
                create_article_template(kw_data["keyword"], kw_data["niche"] or "general")
