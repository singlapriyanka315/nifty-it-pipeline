"""
Rebuild the PDF for a report already saved in Postgres - no fetching, no LLM calls.

    python make_pdf.py          # latest report
    python make_pdf.py 7        # report #7
"""

import sys
from pathlib import Path

from config import INDEX, REPORTS_DIR
from pipeline import db
from pipeline.analyse import compute_stats
from pipeline.pdf import render_pdf


def closes_until(conn, company_id, as_of):
    return [(d, c) for d, c in db.closes_last_year(conn, company_id) if d <= as_of]


def main(report_id=None):
    conn = db.connect()
    if report_id is None:
        report_id = conn.execute("SELECT max(id) AS id FROM reports").fetchone()["id"]
    rep = conn.execute("SELECT * FROM reports WHERE id = %s", (report_id,)).fetchone()
    if rep is None:
        sys.exit(f"No report #{report_id}")

    as_of = rep["as_of_date"]
    index_id = conn.execute("SELECT id FROM companies WHERE symbol = %s", (INDEX["symbol"],)).fetchone()["id"]
    index_stats = compute_stats(closes_until(conn, index_id, as_of))

    companies = []
    rows = conn.execute(
        """
        SELECT c.id, c.name, rs.commentary FROM report_stats rs
        JOIN companies c ON c.id = rs.company_id
        WHERE rs.report_id = %s ORDER BY c.id
        """,
        (report_id,),
    ).fetchall()
    for r in rows:
        news_ids = [x["news_id"] for x in conn.execute(
            """
            SELECT rn.news_id FROM report_news rn JOIN news n ON n.id = rn.news_id
            WHERE rn.report_id = %s AND n.company_id = %s ORDER BY rn.rank
            """,
            (report_id, r["id"]),
        ).fetchall()]
        companies.append({
            "name": r["name"],
            "stats": compute_stats(closes_until(conn, r["id"], as_of)),
            "commentary": r["commentary"],
            "headlines": db.news_by_ids(conn, news_ids),
        })
    conn.close()

    Path(REPORTS_DIR).mkdir(exist_ok=True)
    path = Path(REPORTS_DIR) / f"nifty-it-{as_of:%Y-%m-%d}.pdf"
    render_pdf(path, as_of, INDEX["name"], index_stats, companies, rep["summary"])
    print(f"Report #{report_id} → {path}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
