from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
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

    async def dispatch(self, request, call_next: Callable) -> Response:
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
                return Response(status_code=304, headers=response.headers)

            from starlette.responses import Response as StarletteResponse

            return StarletteResponse(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        return response


def create_app(
    title: str,
    description: str,
    version: str,
    router,
    lifespan: Callable[[FastAPI], AsyncGenerator[None, None]] | None = None,
    settings_class: Any = None,
    health_check: bool = True,
    cache_middleware: bool = False,
    cache_control: str = "public, max-age=60, stale-while-revalidate=300",
) -> FastAPI:
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if cache_middleware:
        app.add_middleware(CacheMiddleware, cache_control=cache_control)

    if health_check:

        @app.get("/health")
        async def health_check_endpoint() -> dict[str, str]:
            return {"status": "ok", "service": title.lower().replace(" ", "-"), "version": version}

    if router is not None:
        app.include_router(router)

    return app


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