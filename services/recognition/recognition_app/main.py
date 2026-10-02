from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from recognition_app.api.routes import router as api_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app) -> AsyncGenerator[None, None]:
    yield

app = FastAPI(
    title="Recognition Service",
    description="Pokemon TCG Card Recognition API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check_endpoint():
    return {"status": "ok", "service": "recognition-service", "version": "0.1.0"}

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)