#!/bin/bash
# PostToolUse hook: prettier で CSS/JS を自動整形し Codex デザインを維持する
f=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))")
case "$f" in
  *.css|*.js)
    /home/takafumikoideru/.npm-global/bin/prettier --write "$f" 2>/dev/null || true
    ;;
esac
