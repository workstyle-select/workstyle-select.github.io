#!/bin/bash
TOKEN="${1:-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}"
REMOTE="https://workstyle-select:${TOKEN}@github.com/workstyle-select/workstyle-select.github.io.git"

if [ -z "$TOKEN" ]; then
  echo "使い方: bash push.sh ghp_xxxx  または TOKEN を push.sh 内に直接書いてください"
  exit 1
fi

echo "==> main ブランチを push..."
git push "$REMOTE" main

echo ""
echo "==> gh-pages ブランチを push..."
git -C /tmp/gh-pages-deploy push "$REMOTE" gh-pages

echo ""
echo "==> 完了！ https://workstyle-select.github.io/"
