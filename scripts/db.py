#!/usr/bin/env python3
"""SQLite database operations for the affiliate system."""

import sqlite3
import os
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "database" / "affiliate.db"
SCHEMA_PATH = Path(__file__).parent.parent / "database" / "schema.sql"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(SCHEMA_PATH.read_text())
    print(f"[DB] Initialized: {DB_PATH}")


def add_keyword(keyword: str, niche: str = None, priority: int = 5) -> int:
    with get_connection() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO keywords (keyword, niche, priority) VALUES (?, ?, ?)",
                (keyword, niche, priority)
            )
            return cur.lastrowid
        except sqlite3.IntegrityError:
            row = conn.execute("SELECT id FROM keywords WHERE keyword = ?", (keyword,)).fetchone()
            return row["id"]


def get_keywords(status: str = None, niche: str = None, limit: int = 50) -> list:
    query = "SELECT * FROM keywords WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if niche:
        query += " AND niche = ?"
        params.append(niche)
    query += " ORDER BY priority ASC, created_at ASC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def update_keyword_status(keyword_id: int, status: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE keywords SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now(), keyword_id)
        )


def add_article(title: str, slug: str, keyword_id: int = None, niche: str = None, content_path: str = None) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT OR REPLACE INTO articles (title, slug, keyword_id, niche, content_path) VALUES (?, ?, ?, ?, ?)",
            (title, slug, keyword_id, niche, content_path)
        )
        return cur.lastrowid


def update_article_status(article_id: int, status: str, url: str = None):
    with get_connection() as conn:
        if url:
            conn.execute(
                "UPDATE articles SET status = ?, published_url = ?, published_at = ?, updated_at = ? WHERE id = ?",
                (status, url, datetime.now(), datetime.now(), article_id)
            )
        else:
            conn.execute(
                "UPDATE articles SET status = ?, updated_at = ? WHERE id = ?",
                (status, datetime.now(), article_id)
            )


def get_articles(status: str = None, limit: int = 50) -> list:
    query = "SELECT * FROM articles WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def add_affiliate_link(article_id: int, program: str, original_url: str,
                        affiliate_url: str, product_name: str = None) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO affiliate_links
               (article_id, program, original_url, affiliate_url, product_name)
               VALUES (?, ?, ?, ?, ?)""",
            (article_id, program, original_url, affiliate_url, product_name)
        )
        return cur.lastrowid


def get_summary() -> dict:
    with get_connection() as conn:
        total_articles = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        published = conn.execute("SELECT COUNT(*) FROM articles WHERE status='published'").fetchone()[0]
        total_keywords = conn.execute("SELECT COUNT(*) FROM keywords").fetchone()[0]
        total_links = conn.execute("SELECT COUNT(*) FROM affiliate_links").fetchone()[0]
        total_earnings = conn.execute("SELECT COALESCE(SUM(earnings_jpy),0) FROM affiliate_links").fetchone()[0]
    return {
        "total_articles": total_articles,
        "published_articles": published,
        "draft_articles": total_articles - published,
        "total_keywords": total_keywords,
        "affiliate_links": total_links,
        "total_earnings_jpy": total_earnings,
    }


if __name__ == "__main__":
    init_db()
    print("[DB] Summary:", get_summary())
