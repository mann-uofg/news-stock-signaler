import os, feedparser
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, create_async_engine
)
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from typing import List

load_dotenv()                       # read .env file
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@timescaledb:5432/newsdb"
)

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

app = FastAPI(title="News Scraper")

class ScrapeRequest(BaseModel):
    feed_url: HttpUrl

class NewsOut(BaseModel):
    ticker: str | None
    headline: str
    timestamp: datetime

class EnrichedOut(BaseModel):
    ticker: str|None
    headline: str
    timestamp: datetime
    sent_score: float
    event_lbl: str

@app.post("/scrape")
async def scrape(req: ScrapeRequest):
    feed = feedparser.parse(str(req.feed_url))
    if feed.bozo:
        raise HTTPException(400, f"Failed to parse feed: {feed.bozo_exception}")

    inserted = 0
    async with SessionLocal() as sess, sess.begin():
        for entry in feed.entries:
            ts = (
                datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                if "published_parsed" in entry
                else datetime.now(timezone.utc)
            )
            stmt = text("""
                INSERT INTO raw_news (ticker, headline, url, timestamp)
                VALUES (NULL, :headline, :url, :ts)
                ON CONFLICT DO NOTHING
            """)
            res = await sess.execute(stmt, {"headline": entry.title, "url": entry.link, "ts": ts})
            inserted += res.rowcount
    return {"inserted": inserted, "total": len(feed.entries)}

@app.get("/latest/{symbol}", response_model=List[NewsOut])
async def latest(symbol: str, limit: int = 20):
    q = text("""
        SELECT ticker, headline, timestamp
        FROM raw_news
        WHERE ticker = :sym
        ORDER BY timestamp DESC
        LIMIT :lim
    """)
    async with SessionLocal() as sess:
        result = await sess.execute(q, {"sym": symbol.upper(), "lim": limit})
        rows = result.mappings().all()        # <= this gives you dict-like rows
    return rows                              # FastAPI/pydantic will handle validation

@app.get("/sentiment/{symbol}", response_model=List[EnrichedOut])
async def latest_sent(symbol: str, limit:int=20):
    q = text("""
      SELECT ticker, headline, timestamp, sent_score, event_lbl
      FROM enriched_news
      WHERE ticker = :sym
      ORDER BY timestamp DESC
      LIMIT :lim
    """)
    async with SessionLocal() as sess:
        rows = (await sess.execute(q, {"sym":symbol.upper(),"lim":limit})
               ).mappings().all()
    return rows