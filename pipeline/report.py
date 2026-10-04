"""Step 4: turn stats + matched headlines into a Markdown report."""

DISCLAIMER = "for educational purposes, not investment advice"


def headline_line(n):
    return f"[{n['published_at']:%Y-%m-%d}] {n['title']} ({n['publisher']})"


def render(as_of, index_name, index_stats, companies, summary=None):
    """
    companies: list of dicts {name, stats, commentary, headlines}
    """
    by_week = sorted(companies, key=lambda c: -c["stats"]["week"])
    best, worst = by_week[0], by_week[-1]

    out = [
        "# NIFTY IT Weekly Review",
        f"_Week ending {as_of:%d %b %Y} · data: Yahoo Finance · {DISCLAIMER}_\n",
    ]
    if summary:
        out += ["## Summary\n", summary + "\n"]

    out += [
        "## Scoreboard\n",
        "| Stock | Price (₹) | 1 Week | 1 Month | 1 Year | From 52W High | Volatility |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, s in [(f"**{index_name}**", index_stats)] + [(c["name"], c["stats"]) for c in by_week]:
        out.append(f"| {name} | {s['price']:,.0f} | {s['week']:+.1f}% | {s['month']:+.1f}% | "
                   f"{s['year']:+.1f}% | {s['from_high']:+.1f}% | {s['volatility']:.0f}% |")
    out.append(f"\nBest this week: **{best['name']}** ({best['stats']['week']:+.1f}%) · "
               f"Weakest: **{worst['name']}** ({worst['stats']['week']:+.1f}%)\n")

    out.append("## Company notes\n")
    for c in companies:
        out.append(f"### {c['name']}\n")
        if c.get("commentary"):
            out.append(c["commentary"] + "\n")
        if c["headlines"]:
            out.append("**Related headlines (via vector search):**\n")
            out += [f"- [{n['title']}]({n['link']}) · {n['publisher']}, {n['published_at']:%d %b %Y}"
                    for n in c["headlines"]]
            out.append("")
        else:
            out.append("_No recent headlines found._\n")
    return "\n".join(out)
