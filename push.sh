#!/bin/bash
# GitHub push スクリプト
# 使い方: bash push.sh ghp_xxxxxxxx

TOKEN=$1
REMOTE="https://workstyle-select:${TOKEN}@github.com/workstyle-select/workstyle-select.github.io.git"

if [ -z "$TOKEN" ]; then
  echo "使い方: bash push.sh ghp_xxxxxxxx"
  exit 1
fi

echo "==> main ブランチを push..."
git push "$REMOTE" main

echo ""
echo "==> サイトをビルド..."
make build

echo ""
echo "==> gh-pages ブランチを更新..."
CURRENT=$(git branch --show-current)

git checkout gh-pages 2>/dev/null || git checkout --orphan gh-pages

# site/ の内容をルートにコピー
cp -r site/. .

git add -A
git commit -m "deploy: $(date '+%Y-%m-%d %H:%M')" 2>/dev/null || echo "(変更なし)"
git push "$REMOTE" gh-pages

git checkout "$CURRENT"
echo ""
echo "==> 完了！ https://workstyle-select.github.io/"
