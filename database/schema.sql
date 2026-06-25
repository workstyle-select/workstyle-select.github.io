-- アフィリエイトシステム データベーススキーマ

CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL UNIQUE,
    niche TEXT,
    search_volume INTEGER DEFAULT 0,
    competition TEXT DEFAULT 'unknown',  -- low/medium/high
    cpc_jpy INTEGER DEFAULT 0,
    status TEXT DEFAULT 'todo',  -- todo/writing/published/archived
    priority INTEGER DEFAULT 5,  -- 1(高)〜10(低)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    keyword_id INTEGER REFERENCES keywords(id),
    niche TEXT,
    status TEXT DEFAULT 'draft',  -- draft/review/published
    word_count INTEGER DEFAULT 0,
    content_path TEXT,  -- content/articles/slug.md へのパス
    published_url TEXT,
    seo_score INTEGER DEFAULT 0,
    pageviews INTEGER DEFAULT 0,
    earnings_jpy INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS affiliate_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER REFERENCES articles(id),
    program TEXT NOT NULL,        -- amazon/rakuten/a8net/etc
    original_url TEXT NOT NULL,
    affiliate_url TEXT NOT NULL,
    product_name TEXT,
    product_asin TEXT,
    clicks INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    earnings_jpy INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS performance (
    article_id INTEGER REFERENCES articles(id),
    date DATE NOT NULL,
    pageviews INTEGER DEFAULT 0,
    unique_visitors INTEGER DEFAULT 0,
    avg_time_seconds INTEGER DEFAULT 0,
    bounce_rate REAL DEFAULT 0,
    affiliate_clicks INTEGER DEFAULT 0,
    affiliate_conversions INTEGER DEFAULT 0,
    earnings_jpy INTEGER DEFAULT 0,
    PRIMARY KEY (article_id, date)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS serp_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword_id INTEGER REFERENCES keywords(id),
    article_id INTEGER REFERENCES articles(id),
    date DATE NOT NULL,
    position INTEGER,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    ctr REAL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
CREATE INDEX IF NOT EXISTS idx_articles_niche ON articles(niche);
CREATE INDEX IF NOT EXISTS idx_keywords_status ON keywords(status);
CREATE INDEX IF NOT EXISTS idx_performance_date ON performance(date);
