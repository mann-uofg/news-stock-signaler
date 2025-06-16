-- infra/sql/init_raw_news.sql  (runs at container-start)
\c newsdb
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

CREATE TABLE IF NOT EXISTS raw_news (
  id        BIGSERIAL PRIMARY KEY,
  ticker    TEXT,                      -- NULL for now; we’ll fill later
  headline  TEXT       NOT NULL,
  url       TEXT       UNIQUE,
  timestamp TIMESTAMPTZ NOT NULL
);

-- make it a hypertable on timestamp
SELECT create_hypertable('raw_news', 'timestamp', if_not_exists => TRUE);
