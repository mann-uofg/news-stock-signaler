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
