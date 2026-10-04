-- NIFTY IT pipeline schema (PostgreSQL)
-- Safe to run many times: everything is CREATE ... IF NOT EXISTS.

-- Stocks and indices we track
CREATE TABLE IF NOT EXISTS companies (
    id        SERIAL PRIMARY KEY,
    name      TEXT NOT NULL UNIQUE,
    symbol    TEXT NOT NULL UNIQUE,          -- Yahoo symbol, e.g. TCS.NS
    is_index  BOOLEAN NOT NULL DEFAULT FALSE
);

-- Daily OHLCV prices, one row per company per trading day
CREATE TABLE IF NOT EXISTS prices (
    company_id  INT  NOT NULL REFERENCES companies(id),
    trade_date  DATE NOT NULL,
    open        NUMERIC(12, 2),
    high        NUMERIC(12, 2),
    low         NUMERIC(12, 2),
    close       NUMERIC(12, 2) NOT NULL,
    volume      BIGINT,
    PRIMARY KEY (company_id, trade_date)
);

-- News headlines. The same id is used in ChromaDB, so a vector
-- search result can always be joined back to this table.
CREATE TABLE IF NOT EXISTS news (
    id            TEXT PRIMARY KEY,           -- Yahoo article uuid
    company_id    INT  NOT NULL REFERENCES companies(id),
    title         TEXT NOT NULL,
    publisher     TEXT,
    published_at  TIMESTAMPTZ NOT NULL,
    link          TEXT,
    fetched_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS news_company_published_idx ON news (company_id, published_at DESC);

-- One row per generated report
CREATE TABLE IF NOT EXISTS reports (
    id          SERIAL PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    as_of_date  DATE NOT NULL,                -- last trading day in the data
    llm_model   TEXT,                         -- NULL when run without an LLM
    summary     TEXT,
    content_md  TEXT NOT NULL
);

-- The numbers behind each report, per company (keeps history week over week)
CREATE TABLE IF NOT EXISTS report_stats (
    report_id      INT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    company_id     INT NOT NULL REFERENCES companies(id),
    price          NUMERIC(12, 2),
    week_pct       NUMERIC(7, 2),
    month_pct      NUMERIC(7, 2),
    year_pct       NUMERIC(7, 2),
    from_high_pct  NUMERIC(7, 2),
    volatility     NUMERIC(7, 2),
    commentary     TEXT,
    PRIMARY KEY (report_id, company_id)
);

-- Which headlines vector search picked for each company in each report
CREATE TABLE IF NOT EXISTS report_news (
    report_id   INT  NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    news_id     TEXT NOT NULL REFERENCES news(id),
    rank        INT  NOT NULL,
    PRIMARY KEY (report_id, news_id)
);
