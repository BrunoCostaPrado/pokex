from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from data_ingestion_app.api.v1.router import router as api_router
from data_ingestion_app.config import settings
from data_ingestion_app.database import init_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app) -> AsyncGenerator[None, None]:
    await init_db()
    yield

app = FastAPI(
    title="Data Ingestion Service",
    description="Pokemon TCG Data Ingestion API",
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
    return {"status": "ok", "service": "data-ingestion-service", "version": "0.1.0"}

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)