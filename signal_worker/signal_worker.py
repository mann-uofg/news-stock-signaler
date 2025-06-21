import os, asyncio, logging, datetime as dt
import pandas as pd
from dotenv import load_dotenv
from prometheus_client import Counter, start_http_server
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

load_dotenv()

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@timescaledb:5432/newsdb"
)
WINDOW      = int(os.getenv("SIGNAL_WINDOW_MIN", "5"))   # minutes
THRESH_RET  = float(os.getenv("RET_THRESHOLD",  "0.003")) # 0.3 %
THRESH_SENT = float(os.getenv("SENT_THRESHOLD", "0.30"))

engine = create_async_engine(DB_URL, echo=False)
Session = sessionmaker(engine, class_=AsyncSession)

signal_inserts = Counter("signal_inserts_total", "signals stored")

UPSERT = text("""
INSERT INTO trade_signals(symbol, ts, px_ret, sent, direction)
VALUES (:sym, :ts, :ret, :sent, :dir)
ON CONFLICT (symbol, ts) DO NOTHING;
""")

SELECT_SQL = """
WITH px AS (
  SELECT symbol, close
  FROM price_history
  WHERE ts >= now() - interval '{w} min'
),
sent AS (
  SELECT ticker AS symbol,
         avg(sent_score) AS sent
  FROM enriched_news
  WHERE timestamp >= now() - interval '{w} min'
  GROUP BY ticker
)
SELECT p.symbol,
       (max(close) - min(close)) / min(close) AS ret,
       coalesce(s.sent,0) AS sent
FROM px p
LEFT JOIN sent s USING(symbol)
GROUP BY p.symbol, s.sent;
""".format(w=WINDOW)

async def compute_and_store():
    async with Session() as s:
        df = (await s.execute(text(SELECT_SQL))).mappings().all()
        for row in df:
            direction = None
            if row["ret"] >  THRESH_RET and row["sent"] >  THRESH_SENT:
                direction = "BUY"
            elif row["ret"] < -THRESH_RET and row["sent"] < -THRESH_SENT:
                direction = "SELL"
            else:
                continue

            await s.execute(
                UPSERT,
                dict(sym=row["symbol"],
                     ts=dt.datetime.utcnow(),
                     ret=row["ret"],
                     sent=row["sent"],
                     dir=direction)
            )
            signal_inserts.inc()
        await s.commit()

async def main_loop():
    start_http_server(9105)          # Prometheus scrape
    logging.info("signal_worker started")
    while True:
        try:
            await compute_and_store()
            logging.info("signal batch committed")
        except Exception as e:
            logging.exception("signal batch failed: %s", e)
        await asyncio.sleep(WINDOW * 60)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(main_loop())
