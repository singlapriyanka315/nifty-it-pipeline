"""Step 2: all maths is done here in Python - never by the LLM."""

import statistics


def pct(a, b):
    return (a / b - 1) * 100


def compute_stats(closes):
    """closes: list of (date, close), oldest first, about one year of trading days."""
    prices = [c for _, c in closes]
    if len(prices) < 22:
        raise ValueError(f"need at least 22 trading days, got {len(prices)}")

    last = prices[-1]
    daily_returns = [prices[i] / prices[i - 1] - 1 for i in range(1, len(prices))]
    return {
        "as_of": closes[-1][0],
        "price": round(last, 2),
        "week": round(pct(last, prices[-6]), 2),    # last 5 trading days
        "month": round(pct(last, prices[-22]), 2),  # ~21 trading days
        "year": round(pct(last, prices[0]), 2),
        "high52": max(prices),
        "low52": min(prices),
        "from_high": round(pct(last, max(prices)), 2),
        # annualised volatility of the last month of daily returns
        "volatility": round(statistics.stdev(daily_returns[-21:]) * 252 ** 0.5 * 100, 2),
    }


def stats_line(s):
    return (f"price ₹{s['price']:,.0f}; week {s['week']:+.1f}%; month {s['month']:+.1f}%; "
            f"1-year {s['year']:+.1f}%; {s['from_high']:+.1f}% from 52-week high; "
            f"volatility {s['volatility']:.0f}%")
