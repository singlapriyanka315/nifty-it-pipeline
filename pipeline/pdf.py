"""Render the weekly report as a PDF with ReportLab.

Uses the built-in Helvetica font so it works on any machine. Helvetica has no
rupee sign, so prices are written as "Rs" and other unsupported characters
from the LLM text are swapped for plain equivalents.
"""

from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from pipeline.report import DISCLAIMER

INK = colors.HexColor("#1f2933")
MUTED = colors.HexColor("#616e7c")
ACCENT = colors.HexColor("#1d4ed8")
RULE = colors.HexColor("#d9dee5")
UP = colors.HexColor("#15803d")
DOWN = colors.HexColor("#b91c1c")
ROW_ALT = colors.HexColor("#f5f7fa")

REPLACE = {
    "₹": "Rs ", "‑": "-", "‐": "-", "−": "-",
    " ": " ", " ": " ", " ": " ", "≈": "~",
}


def clean(text):
    """Make LLM / headline text safe for Helvetica and for Paragraph markup."""
    for bad, good in REPLACE.items():
        text = text.replace(bad, good)
    text = text.encode("cp1252", errors="replace").decode("cp1252")
    return escape(text)


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName="Helvetica-Bold",
                                fontSize=22, leading=26, textColor=INK, alignment=TA_LEFT, spaceAfter=2),
        "sub": ParagraphStyle("sub", parent=base["Normal"], fontSize=9, textColor=MUTED, spaceAfter=10),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold",
                             fontSize=13, textColor=INK, spaceBefore=12, spaceAfter=6, keepWithNext=1),
        "h3": ParagraphStyle("h3", parent=base["Heading3"], fontName="Helvetica-Bold",
                             fontSize=11, textColor=INK, spaceBefore=10, spaceAfter=3),
        "body": ParagraphStyle("body", parent=base["Normal"], fontSize=9.5, leading=13.5, textColor=INK),
        "small": ParagraphStyle("small", parent=base["Normal"], fontSize=8, leading=11, textColor=MUTED),
        "link": ParagraphStyle("link", parent=base["Normal"], fontSize=8.5, leading=11.5,
                               textColor=INK, leftIndent=8, bulletIndent=0),
    }


def _pct(v):
    v = round(v, 1) or 0.0  # turns -0.0 into 0.0
    color = "#15803d" if v > 0.05 else "#b91c1c" if v < -0.05 else "#616e7c"
    return f'<font color="{color}">{v:+.1f}%</font>'


def _scoreboard(index_name, index_stats, companies, st):
    cell = ParagraphStyle("cell", parent=st["body"], fontSize=9, leading=11, alignment=2)
    first = ParagraphStyle("first", parent=cell, alignment=0)
    head = ["Stock", "Price (Rs)", "1 Week", "1 Month", "1 Year", "From 52W High", "Volatility"]
    rows = [[Paragraph(f"<b>{h}</b>", first if i == 0 else cell) for i, h in enumerate(head)]]
    for name, s, bold in [(index_name, index_stats, True)] + [(c["name"], c["stats"], False) for c in companies]:
        label = f"<b>{clean(name)}</b>" if bold else clean(name)
        rows.append([
            Paragraph(label, first),
            Paragraph(f"{s['price']:,.0f}", cell),
            Paragraph(_pct(s["week"]), cell),
            Paragraph(_pct(s["month"]), cell),
            Paragraph(_pct(s["year"]), cell),
            Paragraph(_pct(s["from_high"]), cell),
            Paragraph(f"{s['volatility']:.0f}%", cell),
        ])
    t = Table(rows, colWidths=[34 * mm, 22 * mm, 19 * mm, 19 * mm, 19 * mm, 27 * mm, 20 * mm], repeatRows=1)
    style = [
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
        ("LINEBELOW", (0, 1), (-1, 1), 0.5, RULE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for r in range(2, len(rows), 2):
        style.append(("BACKGROUND", (0, r), (-1, r), ROW_ALT))
    t.setStyle(TableStyle(style))
    return t


def _week_chart(index_name, index_stats, companies):
    """Horizontal bars of 1-week return, index included, sorted best to worst."""
    items = [(c["name"], c["stats"]["week"]) for c in companies] + [(index_name, index_stats["week"])]
    items.sort(key=lambda x: x[1])  # bottom-to-top drawing order -> best ends up on top
    width, height = 170 * mm, 14 * mm + 9 * mm * len(items)

    d = Drawing(width, height)
    chart = HorizontalBarChart()
    chart.x, chart.y = 32 * mm, 8 * mm
    chart.width, chart.height = width - 42 * mm, height - 14 * mm
    chart.data = [[round(v, 1) or 0.0 for _, v in items]]
    chart.categoryAxis.categoryNames = [n for n, _ in items]
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 8
    chart.categoryAxis.labels.fillColor = INK
    chart.categoryAxis.strokeColor = RULE
    chart.categoryAxis.visibleTicks = False
    chart.categoryAxis.joinAxisMode = "left"  # names on the left edge, not on the zero line
    lo, hi = min(v for _, v in items), max(v for _, v in items)
    pad = max(0.5, (hi - lo) * 0.15)
    chart.valueAxis.valueMin = min(0, lo) - pad
    chart.valueAxis.valueMax = max(0, hi) + pad
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fillColor = MUTED
    chart.valueAxis.labelTextFormat = "%+.1f%%"
    chart.valueAxis.strokeColor = RULE
    chart.valueAxis.visibleGrid = True
    chart.valueAxis.gridStrokeColor = RULE
    chart.valueAxis.gridStrokeWidth = 0.3
    chart.bars.strokeColor = None
    chart.barWidth = 6
    for i, (name, v) in enumerate(items):
        chart.bars[(0, i)].fillColor = MUTED if name == index_name else (UP if v >= 0 else DOWN)
    chart.barLabelFormat = "%+.1f%%"
    chart.barLabels.fontName = "Helvetica"
    chart.barLabels.fontSize = 7
    chart.barLabels.fillColor = INK
    chart.barLabels.boxAnchor = "w"  # mirrored automatically for negative bars
    chart.barLabels.dx = 3
    d.add(chart)
    d.add(String(0, height - 5 * mm, "1-week return (grey = index)", fontName="Helvetica", fontSize=8, fillColor=MUTED))
    return d


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.setStrokeColor(RULE)
    canvas.line(doc.leftMargin, 14 * mm, A4[0] - doc.rightMargin, 14 * mm)
    canvas.drawString(doc.leftMargin, 10 * mm, f"NIFTY IT Weekly Review · {DISCLAIMER}")
    canvas.drawRightString(A4[0] - doc.rightMargin, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def render_pdf(path, as_of, index_name, index_stats, companies, summary=None):
    st = _styles()
    by_week = sorted(companies, key=lambda c: -c["stats"]["week"])
    best, worst = by_week[0], by_week[-1]

    story = [
        Paragraph("NIFTY IT Weekly Review", st["title"]),
        Paragraph(f"Week ending {as_of:%d %b %Y} · Data: Yahoo Finance · {DISCLAIMER}", st["sub"]),
    ]
    if summary:
        story += [Paragraph("Summary", st["h2"]), Paragraph(clean(summary), st["body"])]

    story += [
        Paragraph("Scoreboard", st["h2"]),
        _scoreboard(index_name, index_stats, by_week, st),
        Spacer(1, 4),
        Paragraph(f"Best this week: <b>{clean(best['name'])}</b> ({best['stats']['week']:+.1f}%) · "
                  f"Weakest: <b>{clean(worst['name'])}</b> ({worst['stats']['week']:+.1f}%)", st["small"]),
        Spacer(1, 8),
        _week_chart(index_name, index_stats, by_week),
    ]

    for i, c in enumerate(companies):
        s = c["stats"]
        block = [Paragraph("Company notes", st["h2"])] if i == 0 else []
        block += [
            Paragraph(clean(c["name"]), st["h3"]),
            Paragraph(f"Rs {s['price']:,.0f} · week {_pct(s['week'])} · month {_pct(s['month'])} · "
                      f"1 year {_pct(s['year'])}", st["small"]),
            Spacer(1, 3),
        ]
        if c.get("commentary"):
            block += [Paragraph(clean(c["commentary"]), st["body"]), Spacer(1, 4)]
        if c["headlines"]:
            block.append(Paragraph("<b>Related headlines (via vector search)</b>", st["small"]))
            for n in c["headlines"]:
                title = clean(n["title"])
                if n.get("link"):
                    title = f'<a href="{escape(n["link"])}" color="#1d4ed8">{title}</a>'
                block.append(Paragraph(
                    f"{title} <font color='#616e7c'>· {clean(n['publisher'] or '')}, "
                    f"{n['published_at']:%d %b %Y}</font>", st["link"], bulletText="•"))
        else:
            block.append(Paragraph("No recent headlines found.", st["small"]))
        story.append(KeepTogether(block))

    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=20 * mm,
        title="NIFTY IT Weekly Review", author="nifty-it-pipeline",
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
