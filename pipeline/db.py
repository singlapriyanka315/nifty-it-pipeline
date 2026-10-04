"""All PostgreSQL access lives here."""

from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from config import DATABASE_URL

SCHEMA = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


def connect():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_schema(conn):
    conn.execute(SCHEMA.read_text())
    conn.commit()


# ---------------------------------------------------------------- companies
def upsert_company(conn, name, symbol, is_index=False):
    row = conn.execute(
        """
        INSERT INTO companies (name, symbol, is_index) VALUES (%s, %s, %s)
        ON CONFLICT (symbol) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
        """,
        (name, symbol, is_index),
    ).fetchone()
    return row["id"]


# ---------------------------------------------------------------- prices
def upsert_prices(conn, company_id, rows):
    """rows: list of dicts with trade_date, open, high, low, close, volume."""
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO prices (company_id, trade_date, open, high, low, close, volume)
            VALUES (%(company_id)s, %(trade_date)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s)
            ON CONFLICT (company_id, trade_date) DO UPDATE SET
                open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
                close = EXCLUDED.close, volume = EXCLUDED.volume
            """,
            [{**r, "company_id": company_id} for r in rows],
        )


def closes_last_year(conn, company_id):
    """Closing prices for the last 365 days, oldest first."""
    rows = conn.execute(
        """
        SELECT trade_date, close FROM prices
        WHERE company_id = %s
          AND trade_date > (SELECT max(trade_date) FROM prices WHERE company_id = %s) - INTERVAL '365 days'
        ORDER BY trade_date
        """,
        (company_id, company_id),
    ).fetchall()
    return [(r["trade_date"], float(r["close"])) for r in rows]


# ---------------------------------------------------------------- news
def insert_news(conn, company_id, articles):
    """Insert headlines, skipping ones already stored. Returns the newly added ones."""
    added = []
    for a in articles:
        row = conn.execute(
            """
            INSERT INTO news (id, company_id, title, publisher, published_at, link)
            VALUES (%(id)s, %(company_id)s, %(title)s, %(publisher)s, %(published_at)s, %(link)s)
            ON CONFLICT (id) DO NOTHING
            RETURNING id
            """,
            {**a, "company_id": company_id},
        ).fetchone()
        if row:
            added.append(a)
    return added


def news_by_ids(conn, ids):
    if not ids:
        return []
    rows = conn.execute(
        "SELECT id, title, publisher, published_at, link FROM news WHERE id = ANY(%s)", (ids,)
    ).fetchall()
    by_id = {r["id"]: r for r in rows}
    return [by_id[i] for i in ids if i in by_id]  # keep vector-search ranking order


# ---------------------------------------------------------------- reports
def save_report(conn, as_of_date, llm_model, summary, content_md, stats, picked_news):
    """
    stats:       {company_id: {price, week, month, year, from_high, volatility, commentary}}
    picked_news: {company_id: [news_id, ...]}
    """
    report_id = conn.execute(
        """
        INSERT INTO reports (as_of_date, llm_model, summary, content_md)
        VALUES (%s, %s, %s, %s) RETURNING id
        """,
        (as_of_date, llm_model, summary, content_md),
    ).fetchone()["id"]

    for company_id, s in stats.items():
        conn.execute(
            """
            INSERT INTO report_stats (report_id, company_id, price, week_pct, month_pct,
                                      year_pct, from_high_pct, volatility, commentary)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (report_id, company_id, s["price"], s["week"], s["month"], s["year"],
             s["from_high"], s["volatility"], s.get("commentary")),
        )
    for news_ids in picked_news.values():
        for rank, news_id in enumerate(news_ids, start=1):
            conn.execute(
                "INSERT INTO report_news (report_id, news_id, rank) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (report_id, news_id, rank),
            )
    return report_id
