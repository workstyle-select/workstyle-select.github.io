# Codex CLI 自動化プロンプト集

OpenAI Codex CLI (`codex`) と連携するための自動化プロンプトです。

---

## 1. キーワードから記事構造を自動生成

```bash
codex "config/keywords.yamlの'todo'ステータスのキーワードを読み込み、
最も優先度の高いキーワードでcontent/articles/に記事テンプレートを作成してください。
Frontmatterを含むMarkdownファイルとして保存してください。
使用するスクリプト: scripts/content_pipeline.py"
```

## 2. 記事のSEOスコア一括チェック

```bash
codex "content/articles/ディレクトリの全Markdownファイルに対して
scripts/seo.pyを実行し、SEOスコアが60点以下の記事をリストアップしてください。
改善が必要な記事のタイトルとissueをまとめたレポートをconsoleに出力してください"
```

## 3. アフィリエイトリンクの自動挿入

```bash
codex "content/articles/ディレクトリの記事を読み込み、
<!-- AFFILIATE_LINK_N --> プレースホルダーを検出して、
config/settings.yamlのAmazon設定を使って適切なアフィリエイトURLを提案してください。
scripts/link_manager.pyを参照してください"
```

## 4. サイトのビルドと確認

```bash
codex "scripts/site_builder.pyを実行してsite/ディレクトリにHTMLを生成し、
生成されたページ数とエラーがあれば報告してください"
```

## 5. パフォーマンスレポート生成

```bash
codex "scripts/analytics.pyを実行し、
database/affiliate.dbから収益データを集計して
dashboard/data.jsonを更新し、サマリーをコンソールに出力してください"
```

## 6. キーワードリサーチの実行

```bash
codex "scripts/keyword_research.pyを実行して
config/keywords.yamlのseed_keywordsを展開し、
発見したキーワードをdatabase/affiliate.dbに保存してください。
低競合キーワードを優先して上位30件を出力してください"
```

---

## 毎日の自動ルーティン（GitHub Actions）

`.github/workflows/daily.yml` で設定済みの自動タスク:
- 06:00 JST: キーワードリサーチ更新
- 07:00 JST: 前日の記事のSEOチェック
- 08:00 JST: サイトビルド＆デプロイ
- 21:00 JST: アナリティクスデータ更新

---

## Claude Code との連携

Claude Code (`claude`) はコンテンツ生成に使用:

```bash
# 記事の下書きを生成してファイルに保存
claude --print "$(cat prompts/article_writer.md)" > /tmp/draft.md

# SEOレビューを実施
claude --print "$(cat prompts/seo_optimizer.md)" 

# 翻訳・多言語展開（英語版作成）
claude --print "以下の日本語記事を英語のSEO記事に翻訳して:
$(cat content/articles/target-article.md)"
```
