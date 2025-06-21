from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import timedelta, datetime
import os, pandas as pd
from sqlalchemy.ext.asyncio import create_async_engine
from prometheus_client import Counter, generate_latest
from fastapi.responses import PlainTextResponse
from fastapi import FastAPI, HTTPException

DB = os.getenv("DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@timescaledb:5432/newsdb")
engine = create_async_engine(DB, echo=False)

sent_queries = Counter("sentiment_queries_total", "Calls to /correlation")

app = FastAPI(title="Analytics API")

@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return generate_latest()

class CorrOut(BaseModel):
    symbol: str
    pearson_r: float
    n_points: int

@app.get("/correlation/{symbol}", response_model=CorrOut)
async def corr(symbol: str, days: int = 30):
    sym = symbol.upper()
    since = datetime.utcnow() - timedelta(days=days)
    sql = f"""
    SELECT ph.ts, ph.close, en.sent_score
      FROM price_history ph
      JOIN  enriched_news en
        ON en.ticker = '{sym}' AND ph.ts::date = en.timestamp::date
     WHERE ph.symbol = '{sym}' AND ph.ts >= '{since.isoformat()}'
    """
    async with engine.connect() as conn:
        df = pd.read_sql(sql, conn)
    if len(df) < 10:
        raise HTTPException(404, "Not enough overlap")
    r = df["close"].corr(df["sent_score"])
    sent_queries.inc()
    return CorrOut(symbol=sym, pearson_r=float(r), n_points=len(df))

@app.get("/trend/{symbol}")
async def trend(symbol: str, days: int = 30):
    sym = symbol.upper()
    since = datetime.utcnow() - timedelta(days=days)
    sql = f"""
    SELECT ts, close FROM price_history
     WHERE symbol = '{sym}' AND ts >= '{since.isoformat()}'
     ORDER BY ts
    """
    async with engine.connect() as conn:
        price = pd.read_sql(sql, conn)
    sql2 = f"""
    SELECT timestamp, sent_score FROM enriched_news
     WHERE ticker = '{sym}' AND timestamp >= '{since.isoformat()}'
     ORDER BY timestamp
    """
    async with engine.connect() as conn:
        sent = pd.read_sql(sql2, conn)
    return {"price": price.to_dict(orient="records"),
            "sentiment": sent.to_dict(orient="records")}

@app.get("/signals/{symbol}")
async def latest_signal(symbol: str):
    async with Session() as s:
        res = await s.execute(
            text("""
                  SELECT direction, ts
                  FROM trade_signals
                  WHERE symbol = :sym
                  ORDER BY ts DESC
                  LIMIT 1"""),
            {"sym": symbol.upper()}
        )
        row = res.first()
        if not row:
            raise HTTPException(status_code=404, detail="no signal yet")
        return dict(direction=row.direction, ts=row.ts)