"""
NIFTY IT Weekly Review pipeline.

    python main.py

  1. FETCH    prices + headlines from Yahoo Finance        -> PostgreSQL
  2. INDEX    new headlines are embedded                   -> ChromaDB
  3. ANALYSE  returns / volatility computed from Postgres prices
  4. REPORT   vector search picks relevant news, optional LLM writes commentary
              -> reports/<date>.md  and  the reports / report_stats tables
"""

from pathlib import Path

from config import GROQ_API_KEY, INDEX, REPORTS_DIR, STOCKS
from pipeline import db
from pipeline.analyse import compute_stats, stats_line
from pipeline.fetch import fetch_news, fetch_prices
from pipeline.llm import Writer
from pipeline.report import headline_line, render
from pipeline.vectors import NewsIndex

SEARCH_QUERY = "{name} earnings, deals, outlook, share price movement"


def main():
    conn = db.connect()
    db.init_schema(conn)
    news_index = NewsIndex()
    writer = Writer()
    print("LLM:", writer.model if writer.enabled else "off (set GROQ_API_KEY in .env to enable)")

    # ---- 1 + 2. fetch and store
    index_id = db.upsert_company(conn, INDEX["name"], INDEX["symbol"], is_index=True)
    db.upsert_prices(conn, index_id, fetch_prices(INDEX["symbol"]))
    print(f"Fetched {INDEX['name']}")

    company_ids = {}
    for name, cfg in STOCKS.items():
        cid = db.upsert_company(conn, name, cfg["symbol"])
        company_ids[name] = cid
        prices = fetch_prices(cfg["symbol"])
        db.upsert_prices(conn, cid, prices)
        new_articles = db.insert_news(conn, cid, fetch_news(cfg["search"], cfg["keywords"]))
        conn.commit()
        news_index.add(name, new_articles)  # only embed what Postgres hadn't seen yet
        print(f"Fetched {name}: {len(prices)} price rows, {len(new_articles)} new headlines")

    # ---- 3. analyse (from the database, not from the API response)
    index_stats = compute_stats(db.closes_last_year(conn, index_id))
    companies, stats_by_id, picked = [], {}, {}
    for name, cid in company_ids.items():
        s = compute_stats(db.closes_last_year(conn, cid))
        news_ids = news_index.search(name, SEARCH_QUERY.format(name=name))
        headlines = db.news_by_ids(conn, news_ids)
        companies.append({"name": name, "stats": s, "headlines": headlines, "commentary": None})
        stats_by_id[cid] = s
        picked[cid] = news_ids

    # ---- 4. report
    summary = None
    if writer.enabled:
        for c in companies:
            print(f"Writing {c['name']}...")
            c["commentary"] = writer.company_note(
                c["name"], stats_line(c["stats"]), stats_line(index_stats),
                "\n".join(headline_line(n) for n in c["headlines"]),
            )
            stats_by_id[company_ids[c["name"]]]["commentary"] = c["commentary"]
        print("Writing sector summary...")
        summary = writer.sector_summary(
            f"Index: {stats_line(index_stats)}\n"
            + "\n".join(f"{c['name']}: {stats_line(c['stats'])}" for c in companies)
            + "\n\nCompany notes:\n"
            + "\n\n".join(f"{c['name']}: {c['commentary']}" for c in companies if c["commentary"])
        )

    as_of = index_stats["as_of"]
    content = render(as_of, INDEX["name"], index_stats, companies, summary)
    report_id = db.save_report(conn, as_of, writer.model, summary, content, stats_by_id, picked)
    conn.commit()
    conn.close()

    Path(REPORTS_DIR).mkdir(exist_ok=True)
    path = Path(REPORTS_DIR) / f"nifty-it-{as_of:%Y-%m-%d}.md"
    path.write_text(content)
    print(f"\nDone → {path}  (saved as report #{report_id} in Postgres)")


if __name__ == "__main__":
    main()
