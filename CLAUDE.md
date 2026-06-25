# UltiAffi - 半自動アフィリエイトシステム

Claude Code + OpenAI Codex CLI を組み合わせた半自動アフィリエイトサイト構築システム。
有料API連携ゼロで運用可能。

## プロジェクト構成

```
ultimet_affi/
├── config/              # 設定ファイル
│   ├── settings.yaml    # サイト設定・アフィリエイトプログラム設定
│   └── keywords.yaml    # ニッチ別キーワード設定
├── scripts/             # 自動化スクリプト
│   ├── db.py            # SQLiteデータベース操作
│   ├── keyword_research.py  # Google Autocompleteからキーワード収集
│   ├── content_pipeline.py  # 記事テンプレート作成・Claude連携
│   ├── seo.py           # SEOスコア計算・メタタグ生成
│   ├── link_manager.py  # アフィリエイトURL生成・管理
│   ├── site_builder.py  # 静的サイトジェネレーター(Jinja2)
│   └── analytics.py     # 収益集計・ダッシュボード更新
├── prompts/             # Claude/Codex用プロンプトテンプレート
│   ├── article_writer.md     # 記事執筆プロンプト
│   ├── article_outline.md    # アウトライン生成プロンプト
│   ├── seo_optimizer.md      # SEOレビュープロンプト
│   └── codex_automation.md   # Codex CLI自動化コマンド集
├── templates/           # HTMLテンプレート(Jinja2)
│   └── static/style.css # サイトCSS
├── content/articles/    # 記事Markdownファイル群
├── database/            # SQLiteDB + スキーマ
├── site/                # ビルド済み静的サイト(GitHub Pagesへデプロイ)
├── dashboard/           # 収益ダッシュボード(HTML+JS)
├── .github/workflows/   # GitHub Actions (毎日自動実行)
└── Makefile             # ワークフローコマンド

```

## 日次ワークフロー

```
make research       → Google Autocompleteでキーワード収集 (無料)
make new-article    → 記事テンプレート作成
[claude/codex]      → 記事を執筆 (Claude Code / Codex CLI)
make seo-check      → SEOスコア確認
make add-links      → アフィリエイトURL挿入
make publish        → GitHub Pages にデプロイ (無料)
make analytics      → 収益レポート更新
```

## Claude Code でよく使うコマンド

```bash
# 記事アウトライン生成
claude "prompts/article_outline.md の形式でキーワード「ワイヤレスイヤホン おすすめ」のアウトラインをJSON形式で出力して"

# 記事執筆（テンプレートファイルを渡す）
claude "content/articles/xxx.md のコメントに従ってアフィリエイト記事を執筆して。
prompts/article_writer.md の要件を守ること"

# SEOレビュー
claude "content/articles/xxx.md を読んでSEO観点でレビューして。
prompts/seo_optimizer.md の形式で出力して"

# 内部リンク提案
claude "content/articles/内の全記事を確認して、互いに内部リンクを貼るべき記事の組み合わせを提案して"

# 収益改善提案
claude "database/affiliate.db のデータを確認して、収益を増やすための具体的な改善案を3つ提案して"
```

## Codex CLI でよく使うコマンド

```bash
# キーワードを自動リサーチしてDB保存
codex "scripts/keyword_research.pyを実行してDBに保存して"

# 記事SEO一括チェック
codex "content/articles/の全記事にscripts/seo.pyを実行して、スコア60点以下をリストアップして"

# サイトビルド
codex "scripts/site_builder.pyを実行してsite/を生成して"
```

## アフィリエイトプログラム設定

`config/settings.yaml` で設定:
- Amazon アソシエイト: `tag` を設定
- 楽天アフィリエイト: `affiliate_id` を設定
- A8.net: `media_id` を設定
- もしもアフィリエイト: `a8_pid` を設定

## 記事ステータスフロー

```
todo → writing → review → published → archived
```

## データベース構造

- `keywords`: キーワード管理・競合・優先度
- `articles`: 記事管理・公開URL・収益
- `affiliate_links`: リンク別クリック・CV・収益
- `performance`: 日次パフォーマンス記録
- `serp_tracking`: SERP順位推移

## 無料ツール活用

| ツール | 用途 | 制限 |
|--------|------|------|
| Google Autocomplete | キーワード収集 | 礼儀ある間隔が必要 |
| Google Search Console | 順位・CTR確認 | 無料API |
| Google Analytics 4 | アクセス解析 | 無料 |
| GitHub Pages | ホスティング | 無料 |
| GitHub Actions | 自動化 | 2000分/月無料 |
| SQLite | DB | 完全無料 |

## よくある作業

### 新しいニッチを追加する
1. `config/keywords.yaml` の `niches` に追加
2. `make research` でキーワードを収集
3. `config/settings.yaml` に対応するアフィリエイトプログラムを設定

### 記事を公開状態にする
```python
# content/articles/slug.md のfrontmatterを変更
status: "published"
```

### アフィリエイトリンクを挿入する
`<!-- AFFILIATE_LINK_1 -->` を記事内のプレースホルダーとして使用し、
`make add-links SLUG=記事スラッグ` で挿入する。
