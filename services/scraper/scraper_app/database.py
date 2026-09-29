from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from scraper_app.config import settings

engine = create_async_engine(settings.database_url)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
