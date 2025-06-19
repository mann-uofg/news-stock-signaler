import os, asyncio, yfinance as yf, datetime as dt, logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv
from metrics_price import price_upserts
import yfinance as yf
from datetime import datetime, timedelta
import logging
logger = logging.getLogger("price_worker")


load_dotenv()
DB = os.getenv("DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@timescaledb:5432/newsdb"
)
TICKER_LIST = os.getenv("PRICE_SYMBOLS", "AAPL,MSFT,GOOGL,AMZN,TSLA").split(",")

engine = create_async_engine(DB, echo=False, pool_size=4, max_overflow=8)
Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

UPSERT_SQL = text("""
INSERT INTO price_history(symbol, ts, open, high, low, close, volume)
VALUES (:sym,:ts,:o,:h,:l,:c,:v)
ON CONFLICT (symbol, ts) DO UPDATE
SET close = EXCLUDED.close,
    volume = EXCLUDED.volume;
""")

async def fetch_and_store(symbol: str):
    try:
        # Either keep your start/end approach…
        data = yf.download(
                            symbol,
                            period="1d",       # last trading day
                            interval="5m",     # 5-minute bars
                            progress=False,
                            auto_adjust=True,
                            )
        # …or switch to period="5m" which never errors if empty:
        # data = yf.download(symbol, period="5m", interval="1m", progress=False)
    except Exception as e:
        logger.error(f"❌ yfinance error for {symbol!r}: {e}")
        return

    if data.empty:
        logger.info(f"⚠️  no new bars for {symbol!r}")
        return
    ts, row = data.index[-1], data.iloc[-1]
    async with Session() as sess:
        await sess.execute(
            UPSERT_SQL,
            dict(sym=symbol,
                 ts=ts.to_pydatetime(),
                 o=row["Open"], h=row["High"], l=row["Low"],
                 c=row["Close"], v=int(row["Volume"] or 0))
        )
        await sess.commit()
        price_upserts.inc()
        logger.info(f"✅ {symbol!r}: upserted {ts.strftime('%Y-%m-%d %H:%M')} bar")

async def loop():
    while True:
        tasks = [fetch_and_store(s) for s in TICKER_LIST]
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(60)      # every minute

if __name__ == "__main__":
    # configure root logger to show INFO (so logger.info() actually prints)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S"
    )
    logger.info("🔔 price_worker starting up…")
    try:
        asyncio.run(loop())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 price_worker shutting down…")
