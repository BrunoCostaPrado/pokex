from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from data_ingestion_app.config import settings

engine = create_async_engine(settings.database_url)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        yield session


async def init_db() -> None:
    from data_ingestion_app.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
