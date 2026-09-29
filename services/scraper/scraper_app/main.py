import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from pydantic_settings import BaseSettings

from scraper_app.config import settings
from scraper_app.models import Base
from scraper_app.sync import sync_all
from services.shared.fastapi_factory import create_app

engine = create_async_engine(settings.database_url)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


sync_task: asyncio.Task | None = None


async def run_full_sync() -> None:
    await sync_all()


async def _periodic_sync() -> None:
    while True:
        await asyncio.sleep(settings.sync_interval_hours * 3600)
        await run_full_sync()


@asynccontextmanager
async def lifespan(app) -> AsyncGenerator[None, None]:
    await init_db()

    if settings.sync_sets_on_startup:
        await run_full_sync()

    global sync_task
    if settings.sync_interval_hours > 0:
        sync_task = asyncio.create_task(_periodic_sync())

    yield

    if sync_task:
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass


app = create_app(
    title="Scraper Service",
    description="Pokemon TCG Data Scraper",
    version="0.1.0",
    router=None,
    lifespan=lifespan,
    health_check=True,
)

# Add health check manually since router is None
# The health_check endpoint is already added by factory

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
