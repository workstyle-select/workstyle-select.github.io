#!/usr/bin/env python3
"""キーワード・KPIのコンソール表示ユーティリティ"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import db

db.init_db()
mode = sys.argv[1] if len(sys.argv) > 1 else "todo"

if mode == "todo":
    kws = db.get_keywords(status="todo", limit=20)
    print(f"\n未処理キーワード: {len(kws)}件\n")
    for k in kws:
        comp = k.get("competition") or "?"
        kw = k.get("keyword", "")
        niche = k.get("niche") or "-"
        print(f"  [{comp:6}] {kw} ({niche})")
    print()

elif mode == "all":
    for status in ["todo", "writing", "published", "archived"]:
        kws = db.get_keywords(status=status, limit=5)
        if kws:
            print(f"\n[{status}] {len(kws)}件")
            for k in kws:
                print(f"  - {k['keyword']}")
    print()

elif mode == "summary":
    s = db.get_summary()
    print("\n=== UltiAffi KPI ===")
    for k, v in s.items():
        print(f"  {k:<25} {v}")
    print()
