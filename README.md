# NIFTY IT Weekly Review

A data pipeline that tracks the five big Indian IT stocks (TCS, Infosys, Wipro, HCLTech, Tech Mahindra) against the NIFTY IT index, matches price moves to news using vector search, and writes a weekly report.

```
Yahoo Finance ──► PostgreSQL ──► Python stats ──┐
     (news) ──► ChromaDB (vectors) ── search ───┼──► LLM (Groq) ──► report (.md + Postgres)
```

| Layer | Tool | Role |
|---|---|---|
| Data source | yfinance | Daily prices + news headlines, no API key |
| Database | PostgreSQL | Source of truth: companies, prices, news, reports |
| Vectors | ChromaDB | Semantic search over headlines (embeddings made locally) |
| LLM | Groq free tier (optional) | Writes commentary from computed numbers + matched headlines |

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
createdb nifty_it
cp .env.example .env        # add GROQ_API_KEY for AI commentary
```

## Run

```bash
.venv/bin/python main.py
```

Each run upserts prices, stores only new headlines, and saves a report to `reports/` and to the `reports` table. Running it again is safe — nothing is duplicated.

## Database

Schema: [`db/schema.sql`](db/schema.sql)

- `companies` – tracked stocks and the index
- `prices` – daily OHLCV, one row per stock per day
- `news` – headlines; `news.id` is also the ChromaDB id
- `reports` – every generated report (Markdown + summary)
- `report_stats` – the numbers behind each report, per stock
- `report_news` – which headlines vector search chose for each report

Example queries:

```sql
-- Week-over-week history for one stock
SELECT r.as_of_date, rs.week_pct, rs.price
FROM report_stats rs JOIN reports r ON r.id = rs.report_id
JOIN companies c ON c.id = rs.company_id
WHERE c.name = 'Infosys' ORDER BY r.as_of_date;

-- Biggest single-day moves in the last year
SELECT c.name, p.trade_date,
       round((p.close / lag(p.close) OVER w - 1) * 100, 2) AS day_pct
FROM prices p JOIN companies c ON c.id = p.company_id
WINDOW w AS (PARTITION BY p.company_id ORDER BY p.trade_date)
ORDER BY abs(p.close / lag(p.close) OVER w - 1) DESC NULLS LAST LIMIT 10;
```

## Project layout

```
main.py              orchestrates the 4 steps
config.py            stocks, settings, env vars
db/schema.sql        PostgreSQL schema
pipeline/fetch.py    step 1 – Yahoo Finance prices + news
pipeline/db.py       all SQL
pipeline/vectors.py  step 2 – ChromaDB index + search
pipeline/analyse.py  step 3 – returns, volatility (Python, not the LLM)
pipeline/llm.py      optional Groq commentary
pipeline/report.py   step 4 – Markdown rendering
```

_For educational purposes, not investment advice._
