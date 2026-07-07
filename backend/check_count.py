import asyncio, sys
sys.path.append('.')
from app.models import ScamPattern
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, func
from app.config import settings

async def c():
    e = create_async_engine(settings.database_url)
    async with AsyncSession(e) as s:
        r = await s.execute(select(func.count(ScamPattern.id)))
        print(f'Total rows in scam_patterns: {r.scalar()}')
    await e.dispose()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(c())
