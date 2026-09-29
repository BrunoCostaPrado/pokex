# Test configuration for pytest
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, AsyncMock
from functools import wraps
from typing import Callable

# Import real TestClient from starlette (installed and working)
from starlette.testclient import TestClient as RealTestClient
from starlette.applications import Starlette as RealStarlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse, Response as StarletteResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class CacheMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        cache_control: str = "public, max-age=60, stale-while-revalidate=300",
        etag_header: str = "ETag",
    ):
        super().__init__(app)
        self.cache_control = cache_control
        self.etag_header = etag_header

    async def dispatch(self, request, call_next: Callable) -> StarletteResponse:
        if request.method not in ("GET", "HEAD"):
            return await call_next(request)

        response = await call_next(request)

        if 200 <= response.status_code < 300:
            response.headers["Cache-Control"] = self.cache_control

            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            import hashlib

            etag = f'W/"{hashlib.md5(body).hexdigest()}"'
            response.headers[self.etag_header] = etag

            if_none_match = request.headers.get("If-None-Match")
            if if_none_match and if_none_match == etag:
                return StarletteResponse(status_code=304, headers=response.headers)

            return StarletteResponse(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        return response


def cache_response(
    max_age: int = 60,
    stale_while_revalidate: int = 300,
    private: bool = False,
):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            if hasattr(result, "headers"):
                cache_control = f"{'private' if private else 'public'}, max-age={max_age}"
                if stale_while_revalidate:
                    cache_control += f", stale-while-revalidate={stale_while_revalidate}"
                result.headers["Cache-Control"] = cache_control
            return result

        return wrapper

    return decorator

# Create a simple mock engine and session maker that don't use MagicMock spec
class MockEngine:
    pass

class MockSessionMaker:
    def __call__(self, *args, **kwargs):
        return MagicMock()

def mock_create_async_engine(*args, **kwargs):
    return MockEngine()

def mock_async_sessionmaker(*args, **kwargs):
    return MockSessionMaker()

# Create proper mock modules with submodules using real ModuleType
sqlalchemy = ModuleType("sqlalchemy")
sqlalchemy.ext = ModuleType("sqlalchemy.ext")
sqlalchemy.ext.asyncio = ModuleType("sqlalchemy.ext.asyncio")
sqlalchemy.orm = ModuleType("sqlalchemy.orm")
sqlalchemy.dialects = ModuleType("sqlalchemy.dialects")
sqlalchemy.dialects.postgresql = ModuleType("sqlalchemy.dialects.postgresql")

# Add necessary attributes that the service code imports
sqlalchemy.ext.asyncio.AsyncSession = MagicMock
sqlalchemy.ext.asyncio.async_sessionmaker = mock_async_sessionmaker
sqlalchemy.ext.asyncio.create_async_engine = mock_create_async_engine
sqlalchemy.orm.select = MagicMock
sqlalchemy.orm.declarative_base = MagicMock
sqlalchemy.orm.DeclarativeBase = MagicMock
sqlalchemy.orm.Mapped = lambda x: x  # pass through
sqlalchemy.orm.mapped_column = lambda *args, **kwargs: None  # return None
sqlalchemy.orm.relationship = lambda *args, **kwargs: None  # return None
sqlalchemy.select = sqlalchemy.orm.select  # for "from sqlalchemy import select"
sqlalchemy.desc = MagicMock  # for "from sqlalchemy import desc"

# SQLAlchemy types - return simple classes that can be called
class MockType:
    def __init__(self, *args, **kwargs):
        pass
    def __call__(self, *args, **kwargs):
        return self

sqlalchemy.JSON = MockType
sqlalchemy.DateTime = MockType
sqlalchemy.Float = MockType
sqlalchemy.ForeignKey = MockType
sqlalchemy.Integer = MockType
sqlalchemy.String = MockType
sqlalchemy.Text = MockType
sqlalchemy.dialects.postgresql.ARRAY = MockType

sys.modules["sqlalchemy"] = sqlalchemy
sys.modules["sqlalchemy.ext"] = sqlalchemy.ext
sys.modules["sqlalchemy.ext.asyncio"] = sqlalchemy.ext.asyncio
sys.modules["sqlalchemy.orm"] = sqlalchemy.orm
sys.modules["sqlalchemy.dialects"] = sqlalchemy.dialects
sys.modules["sqlalchemy.dialects.postgresql"] = sqlalchemy.dialects.postgresql

# pydantic mocks
pydantic = ModuleType("pydantic")
pydantic.BaseModel = MagicMock
pydantic.BaseSettings = MagicMock
pydantic.ConfigDict = MagicMock
pydantic.Field = MagicMock
sys.modules["pydantic"] = pydantic

pydantic_settings = ModuleType("pydantic_settings")
pydantic_settings.BaseSettings = MagicMock
sys.modules["pydantic_settings"] = pydantic_settings

# redis mocks
redis = ModuleType("redis")
redis.asyncio = ModuleType("redis.asyncio")
redis.asyncio.ConnectionPool = MagicMock
redis.asyncio.ConnectionPool.from_url = MagicMock

# Redis() should return an AsyncMock with aclose
def mock_redis_constructor(*args, **kwargs):
    mock_client = AsyncMock()
    mock_client.aclose = AsyncMock()
    return mock_client

redis.asyncio.Redis = mock_redis_constructor
sys.modules["redis"] = redis
sys.modules["redis.asyncio"] = redis.asyncio

# Mock external dependencies BEFORE any imports
# This must happen before service modules are imported
# DO NOT mock service's own modules (scraper_app.*, data_ingestion_app.*) - they need to import normally
# DO NOT mock httpx - tests need real httpx for spec
sys.modules["psycopg"] = ModuleType("psycopg")
sys.modules["asyncpg"] = ModuleType("asyncpg")

# Mock boto3 and botocore for data-ingestion service
sys.modules["boto3"] = ModuleType("boto3")
sys.modules["boto3.client"] = MagicMock
sys.modules["botocore"] = ModuleType("botocore")
sys.modules["botocore.config"] = ModuleType("botocore.config")
sys.modules["botocore.config"].Config = MagicMock

# services.shared.fastapi_factory - mock implementation using starlette (installed)
# This creates a starlette app compatible with TestClient
def mock_create_app(
    title: str = "",
    description: str = "",
    version: str = "",
    router = None,
    lifespan = None,
    settings_class = None,
    health_check: bool = True,
    cache_middleware: bool = False,
    cache_control: str = "public, max-age=60, stale-while-revalidate=300",
):
    """Create a starlette app that mimics fastapi_factory.create_app behavior."""
    
    async def health_check_endpoint(request):
        return JSONResponse({
            "status": "ok",
            "service": title.lower().replace(" ", "-"),
            "version": version
        })
    
    routes = []
    if health_check:
        routes.append(Route("/health", health_check_endpoint, methods=["GET"]))
    
    if router is not None:
        # Include router routes - router should have .routes attribute
        if hasattr(router, "routes"):
            routes.extend(router.routes)
        else:
            # Try to include as Mount
            routes.append(Mount("", app=router))
    
    middleware = [
        Middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    ]
    
    app = RealStarlette(
        routes=routes,
        middleware=middleware,
        lifespan=lifespan,
    )
    app.title = title
    app.description = description
    app.version = version
    return app

services = ModuleType("services")
services.shared = ModuleType("services.shared")
services.shared.fastapi_factory = ModuleType("services.shared.fastapi_factory")
services.shared.fastapi_factory.create_app = mock_create_app
services.shared.fastapi_factory.CacheMiddleware = CacheMiddleware
services.shared.fastapi_factory.cache_response = cache_response
sys.modules["services"] = services
sys.modules["services.shared"] = services.shared
sys.modules["services.shared.fastapi_factory"] = services.shared.fastapi_factory

# recognition_app is a real package in services/recognition/recognition_app - don't mock it
# The sys.path insertion below makes it importable

# Mock fastapi module to provide TestClient
# Use starlette's TestClient which works
fastapi = ModuleType("fastapi")
fastapi.FastAPI = RealStarlette  # Use starlette as FastAPI substitute

# Create a mock APIRouter that captures routes
class MockAPIRouter:
    def __init__(self, *args, **kwargs):
        self.routes = []
        self.prefix = ""
        self.tags = []
    
    def get(self, path: str, *args, **kwargs):
        def decorator(func):
            from starlette.routing import Route
            self.routes.append(Route(self.prefix + path, func, methods=["GET"]))
            return func
        return decorator
    
    def post(self, path: str, *args, **kwargs):
        def decorator(func):
            from starlette.routing import Route
            self.routes.append(Route(self.prefix + path, func, methods=["POST"]))
            return func
        return decorator
    
    def put(self, path: str, *args, **kwargs):
        def decorator(func):
            from starlette.routing import Route
            self.routes.append(Route(self.prefix + path, func, methods=["PUT"]))
            return func
        return decorator
    
    def delete(self, path: str, *args, **kwargs):
        def decorator(func):
            from starlette.routing import Route
            self.routes.append(Route(self.prefix + path, func, methods=["DELETE"]))
            return func
        return decorator
    
    def include_router(self, other_router, *args, **kwargs):
        if hasattr(other_router, "routes"):
            self.routes.extend(other_router.routes)

fastapi.APIRouter = MockAPIRouter
fastapi.Depends = MagicMock
class MockHTTPException(Exception):
    def __init__(self, status_code: int, detail: str = ""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)

fastapi.HTTPException = MockHTTPException
fastapi.Request = MagicMock
fastapi.Response = StarletteResponse
fastapi.File = MagicMock
class MockUploadFile:
    def __init__(self, filename="test.jpg", content_type="image/jpeg", content=b"fake image"):
        self.filename = filename
        self.content_type = content_type
        self._content = content
    
    async def read(self):
        return self._content
    
    async def seek(self, pos):
        pass
    
    async def close(self):
        pass

fastapi.UploadFile = MockUploadFile
fastapi.Query = MagicMock
fastapi.status = ModuleType("status")
fastapi.status.HTTP_200_OK = 200
fastapi.status.HTTP_201_CREATED = 201
fastapi.status.HTTP_204_NO_CONTENT = 204
fastapi.status.HTTP_400_BAD_REQUEST = 400
fastapi.status.HTTP_404_NOT_FOUND = 404
fastapi.status.HTTP_413_REQUEST_ENTITY_TOO_LARGE = 413
fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY = 422
fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR = 500
fastapi.testclient = ModuleType("fastapi.testclient")
fastapi.testclient.TestClient = RealTestClient
sys.modules["fastapi"] = fastapi
sys.modules["fastapi.routing"] = ModuleType("fastapi.routing")
sys.modules["fastapi.testclient"] = fastapi.testclient

# Mock starlette for TestClient - use real TestClient
starlette = ModuleType("starlette")
starlette.testclient = ModuleType("starlette.testclient")
starlette.testclient.TestClient = RealTestClient
starlette.responses = ModuleType("starlette.responses")
starlette.responses.JSONResponse = JSONResponse
starlette.responses.Response = StarletteResponse
starlette.middleware = ModuleType("starlette.middleware")
starlette.middleware.cors = ModuleType("starlette.middleware.cors")
starlette.middleware.cors.CORSMiddleware = CORSMiddleware
starlette.middleware.base = ModuleType("starlette.middleware.base")
starlette.middleware.base.BaseHTTPMiddleware = MagicMock
starlette.requests = ModuleType("starlette.requests")
starlette.requests.Request = MagicMock
starlette.types = ModuleType("starlette.types")
starlette.types.ASGIApp = MagicMock
starlette.applications = ModuleType("starlette.applications")
starlette.applications.Starlette = RealStarlette
starlette.routing = ModuleType("starlette.routing")
starlette.routing.Route = Route
starlette.routing.Mount = Mount
sys.modules["starlette"] = starlette
sys.modules["starlette.testclient"] = starlette.testclient
sys.modules["starlette.responses"] = starlette.responses
sys.modules["starlette.middleware"] = starlette.middleware
sys.modules["starlette.middleware.cors"] = starlette.middleware.cors
sys.modules["starlette.middleware.base"] = starlette.middleware.base
sys.modules["starlette.requests"] = starlette.requests
sys.modules["starlette.types"] = starlette.types
sys.modules["starlette.applications"] = starlette.applications
sys.modules["starlette.routing"] = starlette.routing

print("CONFTEST LOADED", file=sys.stderr)

# Add service parent directories so packages are importable
# Order matters: insert in reverse so recognition ends up first in path
recognition_parent = Path(__file__).parent.parent.parent / "services" / "recognition"
sys.path.insert(0, str(recognition_parent))
print(f"Added recognition: {recognition_parent}", file=sys.stderr)

data_ingestion_parent = Path(__file__).parent.parent.parent / "services" / "data-ingestion"
sys.path.insert(0, str(data_ingestion_parent))
print(f"Added data-ingestion: {data_ingestion_parent}", file=sys.stderr)

scraper_parent = Path(__file__).parent.parent.parent / "services" / "scraper"
sys.path.insert(0, str(scraper_parent))
print(f"Added scraper: {scraper_parent}", file=sys.stderr)

print("Final sys.path:", file=sys.stderr)
for p in sys.path:
    if 'services' in p:
        print(f"  {p}", file=sys.stderr)