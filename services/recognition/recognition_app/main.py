from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from recognition_app.api.routes import router as api_router
from services.shared.fastapi_factory import create_app


@asynccontextmanager
async def lifespan(app) -> AsyncGenerator[None, None]:
    yield


app = create_app(
    title="Recognition Service",
    description="Pokemon TCG Card Recognition API",
    version="0.1.0",
    router=api_router,
    lifespan=lifespan,
    health_check=True,
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
