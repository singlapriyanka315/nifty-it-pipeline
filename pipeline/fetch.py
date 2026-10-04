"""Step 1: get raw data from Yahoo Finance (no API key needed)."""

import math
from datetime import datetime, timezone

import yfinance as yf


def fetch_prices(symbol, period="1y"):
    hist = yf.Ticker(symbol).history(period=period)
    rows = []
    for ts, r in hist.iterrows():
        if math.isnan(r["Close"]):
            continue
        rows.append({
            "trade_date": ts.date(),
            "open": round(float(r["Open"]), 2),
            "high": round(float(r["High"]), 2),
            "low": round(float(r["Low"]), 2),
            "close": round(float(r["Close"]), 2),
            "volume": int(r["Volume"]) if not math.isnan(r["Volume"]) else None,
        })
    return rows


def fetch_news(search, keywords, count=20):
    """Headlines that actually mention the company, with syndicated duplicates removed."""
    articles, seen_titles = [], set()
    for a in yf.Search(search, news_count=count).news:
        title = a.get("title", "").strip()
        key = title.lower()
        if not title or key in seen_titles or not any(k in key for k in keywords):
            continue
        seen_titles.add(key)
        articles.append({
            "id": a["uuid"],
            "title": title,
            "publisher": a.get("publisher"),
            "published_at": datetime.fromtimestamp(a["providerPublishTime"], timezone.utc),
            "link": a.get("link"),
        })
    return articles
