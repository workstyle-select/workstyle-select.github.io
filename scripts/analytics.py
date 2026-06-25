#!/usr/bin/env python3
"""
アナリティクス集計ダッシュボード
- Google Search Console API（無料・OAuth）からSERP順位取得
- DBのパフォーマンスデータを集計
- 収益レポート生成
有料API不要（Google Search Console APIは無料）
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta, date

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import db


def get_earnings_report(days: int = 30) -> dict:
    """収益レポートを生成"""
    with db.get_connection() as conn:
        # 記事別収益
        article_earnings = conn.execute("""
            SELECT a.title, a.slug, a.niche,
                   COALESCE(SUM(al.earnings_jpy), 0) as earnings,
                   COALESCE(SUM(al.clicks), 0) as clicks,
                   COALESCE(SUM(al.conversions), 0) as conversions
            FROM articles a
            LEFT JOIN affiliate_links al ON a.id = al.article_id
            WHERE a.status = 'published'
            GROUP BY a.id
            ORDER BY earnings DESC
            LIMIT 20
        """).fetchall()

        # プログラム別収益
        program_earnings = conn.execute("""
            SELECT program,
                   COALESCE(SUM(earnings_jpy), 0) as earnings,
                   COALESCE(SUM(clicks), 0) as clicks,
                   COALESCE(SUM(conversions), 0) as conversions
            FROM affiliate_links
            GROUP BY program
            ORDER BY earnings DESC
        """).fetchall()

        total = conn.execute("SELECT COALESCE(SUM(earnings_jpy), 0) FROM affiliate_links").fetchone()[0]

    return {
        "period_days": days,
        "total_earnings_jpy": total,
        "articles": [dict(r) for r in article_earnings],
        "programs": [dict(r) for r in program_earnings],
        "generated_at": datetime.now().isoformat(),
    }


def get_keyword_performance() -> list[dict]:
    """キーワード別パフォーマンスを取得"""
    with db.get_connection() as conn:
        rows = conn.execute("""
            SELECT k.keyword, k.niche, k.competition, k.status,
                   a.title, a.published_url,
                   COALESCE(st.position, 0) as position,
                   COALESCE(st.impressions, 0) as impressions,
                   COALESCE(st.clicks, 0) as gsc_clicks
            FROM keywords k
            LEFT JOIN articles a ON a.keyword_id = k.id
            LEFT JOIN serp_tracking st ON st.keyword_id = k.id
            ORDER BY st.position ASC NULLS LAST
            LIMIT 50
        """).fetchall()
    return [dict(r) for r in rows]


def generate_dashboard_data() -> dict:
    """ダッシュボード用JSONデータを生成"""
    summary = db.get_summary()
    earnings = get_earnings_report()
    keywords = get_keyword_performance()

    top_articles = [
        a for a in earnings["articles"] if a["earnings"] > 0
    ][:10]

    return {
        "summary": summary,
        "earnings": {
            "total_jpy": earnings["total_earnings_jpy"],
            "by_program": earnings["programs"],
            "top_articles": top_articles,
        },
        "keywords": {
            "top_ranking": [k for k in keywords if k["position"] > 0][:10],
            "todo": db.get_keywords(status="todo", limit=10),
            "writing": db.get_keywords(status="writing", limit=10),
        },
        "recent_articles": db.get_articles(status="published", limit=10),
        "generated_at": datetime.now().isoformat(),
    }


def update_dashboard_html():
    """ダッシュボードHTMLを最新データで更新"""
    data = generate_dashboard_data()
    data_json = json.dumps(data, ensure_ascii=False, indent=2)

    dashboard_dir = ROOT / "dashboard"
    data_path = dashboard_dir / "data.json"
    data_path.write_text(data_json, encoding="utf-8")
    print(f"[ANALYTICS] Dashboard data updated: {data_path}")
    return data


def print_console_report():
    """コンソールに収益サマリーを表示"""
    summary = db.get_summary()
    earnings = get_earnings_report()

    print("\n" + "="*60)
    print("  UltiAffi 収益レポート")
    print("="*60)
    print(f"  公開記事数:      {summary['published_articles']:>8}本")
    print(f"  下書き記事数:    {summary['draft_articles']:>8}本")
    print(f"  キーワード数:    {summary['total_keywords']:>8}個")
    print(f"  アフィリンク数:  {summary['affiliate_links']:>8}個")
    print(f"  累計収益:        ¥{summary['total_earnings_jpy']:>7,}")
    print("="*60)

    if earnings["programs"]:
        print("\nプログラム別収益:")
        for prog in earnings["programs"]:
            print(f"  {prog['program']:<12} ¥{prog['earnings']:>6,} / {prog['clicks']}clicks / {prog['conversions']}cv")

    if earnings["articles"][:5]:
        print("\n上位記事:")
        for i, a in enumerate(earnings["articles"][:5], 1):
            print(f"  {i}. {a['title'][:40]} ... ¥{a['earnings']:,}")

    print("="*60)


if __name__ == "__main__":
    db.init_db()
    print_console_report()
    update_dashboard_html()
