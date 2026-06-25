PYTHON := .venv/bin/python
SHELL  := /bin/bash

.DEFAULT_GOAL := help

# ─────────────────────────────────────────────
# 初期セットアップ
# ─────────────────────────────────────────────

.PHONY: setup
setup: ## 初回セットアップ（venv作成・DB初期化）
	@echo "==> Python venv をセットアップ中..."
	python3 -m venv .venv
	.venv/bin/pip install -q jinja2 pyyaml python-slugify feedgenerator requests beautifulsoup4
	@echo "==> データベースを初期化中..."
	$(PYTHON) scripts/db.py
	@echo "==> セットアップ完了！"
	@echo ""
	@echo "次のステップ:"
	@echo "  1. config/settings.yaml にアフィリエイトIDを設定"
	@echo "  2. make research でキーワードリサーチ"
	@echo "  3. make workflow でワークフロー確認"

# ─────────────────────────────────────────────
# キーワードリサーチ
# ─────────────────────────────────────────────

.PHONY: research
research: ## キーワードリサーチを実行（Google Autocomplete）
	$(PYTHON) scripts/keyword_research.py

.PHONY: keywords-todo
keywords-todo: ## 未処理の優先キーワードを表示
	@$(PYTHON) scripts/show_keywords.py todo

.PHONY: keywords-all
keywords-all: ## 全キーワードをステータス別に表示
	@$(PYTHON) scripts/show_keywords.py all

# ─────────────────────────────────────────────
# コンテンツ生成
# ─────────────────────────────────────────────

.PHONY: workflow
workflow: ## コンテンツ生成ワークフローを表示
	$(PYTHON) scripts/content_pipeline.py workflow

.PHONY: new-article
new-article: ## 記事テンプレートを作成（KEYWORD="..." NICHE="..." を指定）
ifndef KEYWORD
	@echo "使い方: make new-article KEYWORD='ワイヤレスイヤホン おすすめ' NICHE=gadgets"
	@exit 1
endif
	$(PYTHON) scripts/content_pipeline.py new --keyword "$(KEYWORD)" --niche "$(or $(NICHE),general)"
	@echo ""
	@echo "次: claude を起動して記事を執筆してください"
	@echo "  $$ claude"
	@echo "  > prompts/article_writer.md の内容を参考に記事を書いて: $(KEYWORD)"

.PHONY: batch-articles
batch-articles: ## DBの未処理KWから記事テンプレートをバッチ作成（上位5件）
	$(PYTHON) scripts/content_pipeline.py batch

.PHONY: claude-prompt
claude-prompt: ## Claude Codeへのプロンプトを出力（KEYWORD="..." を指定）
ifndef KEYWORD
	@echo "使い方: make claude-prompt KEYWORD='スマートウォッチ おすすめ'"
	@exit 1
endif
	$(PYTHON) scripts/content_pipeline.py claude-cmd --keyword "$(KEYWORD)"

# ─────────────────────────────────────────────
# SEOチェック
# ─────────────────────────────────────────────

.PHONY: seo-check
seo-check: ## 記事のSEOスコアをチェック（SLUG="..." を指定）
ifndef SLUG
	@echo "使い方: make seo-check SLUG=wirelessearphone-recommendation"
	@exit 1
endif
	$(PYTHON) scripts/seo.py "$(SLUG)"

.PHONY: seo-all
seo-all: ## 全記事のSEOスコアを一括チェック
	@for f in content/articles/*.md; do \
		slug=$$(basename "$$f" .md); \
		echo "--- $$slug ---"; \
		$(PYTHON) scripts/seo.py "$$slug" 2>/dev/null | grep "SEO スコア" || echo "  [SKIP]"; \
	done

# ─────────────────────────────────────────────
# アフィリエイトリンク
# ─────────────────────────────────────────────

.PHONY: add-links
add-links: ## アフィリエイトリンクを管理（インタラクティブ）
	$(PYTHON) scripts/link_manager.py build

.PHONY: demo-link
demo-link: ## リンク生成デモ
	$(PYTHON) scripts/link_manager.py

# ─────────────────────────────────────────────
# サイトビルド＆デプロイ
# ─────────────────────────────────────────────

.PHONY: build
build: ## 静的サイトをビルド（site/ディレクトリに出力）
	$(PYTHON) scripts/site_builder.py

.PHONY: preview
preview: build ## サイトをローカルでプレビュー（ポート8000）
	@echo "プレビュー: http://localhost:8000"
	cd site && python3 -m http.server 8000

.PHONY: publish
publish: build ## サイトをGitHub Pagesに公開
	@if [ ! -d site ]; then echo "[ERROR] まず make build を実行してください"; exit 1; fi
	@if ! git remote get-url origin >/dev/null 2>&1; then \
		echo "[ERROR] git remoteが設定されていません"; \
		echo "  $$ git remote add origin https://github.com/USER/REPO.git"; \
		exit 1; \
	fi
	@echo "==> GitHub Pages にデプロイ中..."
	@if git show-ref --verify --quiet refs/heads/gh-pages; then \
		git checkout gh-pages; \
	else \
		git checkout --orphan gh-pages; \
		git rm -rf . 2>/dev/null || true; \
	fi
	cp -r site/* . 2>/dev/null || true
	git add -A
	git commit -m "deploy: $(shell date '+%Y-%m-%d %H:%M')" || echo "変更なし"
	git push origin gh-pages
	git checkout main

# ─────────────────────────────────────────────
# アナリティクス
# ─────────────────────────────────────────────

.PHONY: analytics
analytics: ## 収益レポートを生成してダッシュボードを更新
	$(PYTHON) scripts/analytics.py

.PHONY: dashboard
dashboard: analytics ## ダッシュボードをブラウザで開く
	@echo "ダッシュボード: dashboard/index.html"
	@if command -v xdg-open >/dev/null; then xdg-open dashboard/index.html; fi

.PHONY: summary
summary: ## 現在のKPIサマリーを表示
	@$(PYTHON) scripts/show_keywords.py summary

# ─────────────────────────────────────────────
# Git操作
# ─────────────────────────────────────────────

.PHONY: init-repo
init-repo: ## Gitリポジトリを初期化してGitHubにプッシュ
	git init
	git add .
	git commit -m "initial: UltiAffi affiliate system"
	@echo ""
	@echo "GitHubでリポジトリを作成後:"
	@echo "  $$ git remote add origin https://github.com/USER/REPO.git"
	@echo "  $$ git push -u origin main"

# ─────────────────────────────────────────────
# ヘルプ
# ─────────────────────────────────────────────

.PHONY: help
help: ## このヘルプを表示
	@echo ""
	@echo "  UltiAffi - 半自動アフィリエイトシステム"
	@echo "  Claude Code + Codex CLI 連携"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  典型的なワークフロー:"
	@echo "    make setup → make research → make new-article KEYWORD='...' → (claude) → make seo-check SLUG=... → make publish"
	@echo ""
