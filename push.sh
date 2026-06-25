#!/bin/bash
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
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TMP_DIR=$(mktemp -d)
cp -r "$REPO_DIR/site/." "$TMP_DIR/"

CURRENT=$(git branch --show-current)
git checkout gh-pages 2>/dev/null || git checkout --orphan gh-pages

# site/ 以外のファイルをすべて削除してからクリーンデプロイ
git rm -rf . --quiet 2>/dev/null || true
cp -r "$TMP_DIR/." .
rm -rf "$TMP_DIR"

git add -A
git commit -m "deploy: $(date '+%Y-%m-%d %H:%M')" 2>/dev/null || echo "(変更なし)"
git push "$REMOTE" gh-pages

git checkout "$CURRENT"

echo ""
echo "==> 完了！ https://workstyle-select.github.io/"
