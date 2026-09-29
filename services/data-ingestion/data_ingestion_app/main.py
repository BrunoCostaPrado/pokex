from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from data_ingestion_app.api.v1.router import router as api_router
from data_ingestion_app.config import settings
from data_ingestion_app.database import init_db
from services.shared.fastapi_factory import create_app


@asynccontextmanager
async def lifespan(app) -> AsyncGenerator[None, None]:
    await init_db()
    yield


app = create_app(
    title="Data Ingestion Service",
    description="Pokemon TCG Data Ingestion API",
    version="0.1.0",
    router=api_router,
    lifespan=lifespan,
    cache_middleware=True,
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
