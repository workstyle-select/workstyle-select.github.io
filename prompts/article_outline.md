# 記事アウトライン生成プロンプト

キーワード「{{keyword}}」（ニッチ: {{niche}}）のアフィリエイト記事のアウトラインを作成してください。

## 出力形式

以下のJSON形式で出力してください:

```json
{
  "keyword": "{{keyword}}",
  "suggested_title": "【2026年最新】...",
  "meta_description": "120〜160字のメタディスクリプション",
  "search_intent": "informational|commercial|transactional",
  "target_audience": "ターゲット読者の説明",
  "outline": [
    {
      "level": 2,
      "heading": "H2見出し",
      "subheadings": [
        {"level": 3, "heading": "H3見出し", "notes": "ここで書く内容のメモ"}
      ]
    }
  ],
  "faq_questions": [
    "よくある質問1",
    "よくある質問2",
    "よくある質問3"
  ],
  "affiliate_opportunities": [
    {
      "section": "どのセクションで",
      "product_type": "どんな商品",
      "program": "amazon|rakuten|a8net"
    }
  ],
  "related_keywords": ["関連キーワード1", "関連キーワード2"],
  "estimated_word_count": 3000,
  "difficulty": "low|medium|high"
}
```

## 注意点
- 検索意図を正確に把握してください
- 購買意欲の高いユーザーを想定した構成にしてください
- FAQは実際にGoogleで検索されそうな質問にしてください
- アフィリエイト機会は自然な形で記事に組み込めるものにしてください
