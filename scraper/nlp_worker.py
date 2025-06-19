import asyncio, os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from nlp.sentiment import score as sent_score
from nlp.events    import label as event_label
from dotenv import load_dotenv

load_dotenv()
DB = os.getenv("DATABASE_URL",
              "postgresql+asyncpg://postgres:postgres@timescaledb:5432/newsdb")
engine = create_async_engine(DB, echo=False)
Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# pull 500 unprocessed
SELECT_RAW = """
SELECT id, ticker, headline, timestamp
FROM raw_news
WHERE id NOT IN (SELECT raw_id FROM enriched_news)
ORDER BY timestamp
LIMIT 500;
"""
INSERT_ENRICH = """
INSERT INTO enriched_news
(raw_id, ticker, headline, timestamp, sent_score, event_lbl)
VALUES (:rid, :tic, :head, :ts, :score, :lbl)
"""

async def loop():
    while True:
        async with Session() as s:
            rows = (await s.execute(text(SELECT_RAW))).all()
            if not rows:
                await asyncio.sleep(30)
                continue
            for rid, tic, head, ts in rows:
                score = sent_score(head)
                lbl   = event_label(head)
                await s.execute(text(INSERT_ENRICH),
                                dict(rid=rid,tic=tic,head=head,
                                     ts=ts,score=score,lbl=lbl))
            await s.commit()
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(loop())
