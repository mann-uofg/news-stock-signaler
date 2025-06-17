import asyncio, os
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from ticker_matcher import match
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@timescaledb:5432/newsdb"
)
engine = create_async_engine(DATABASE_URL, echo=False)
Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

BATCH = """
SELECT id, headline
FROM raw_news
WHERE ticker IS NULL
ORDER BY id
LIMIT 500;
"""

UPDATE = """
UPDATE raw_news
SET ticker = :sym
WHERE id = :id;
"""

async def worker():
    while True:
        async with Session() as s:
            rows = (await s.execute(text(BATCH))).fetchall()
            if not rows:
                await asyncio.sleep(30)
                continue
            for _id, headline in rows:
                sym = match(headline)
                if sym:
                    await s.execute(text(UPDATE), {"sym": sym, "id": _id})
            await s.commit()
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(worker())
