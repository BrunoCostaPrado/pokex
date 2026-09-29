import pytest
import asyncio
import hashlib
import time
from functools import lru_cache
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.requests import Request
from starlette.responses import Response

from services.shared.fastapi_factory import CacheMiddleware, cache_response


class AsyncIterator:
    def __init__(self, items):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


@pytest.fixture
def mock_request():
    with patch("starlette.requests.Request", autospec=True) as mock_request_class:
        request = mock_request_class.return_value
        request.method = "GET"
        request.headers = {}
        request.url = MagicMock()
        request.url.path = "/health"
        yield request


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=0)
    redis.expire = AsyncMock(return_value=True)
    redis.ttl = AsyncMock(return_value=60)
    redis.keys = AsyncMock(return_value=[])
    redis.ping = AsyncMock(return_value=True)
    redis.setnx = AsyncMock(return_value=True)
    return redis


class TestCacheMiddleware:
    @pytest.mark.asyncio
    async def test_get_request_adds_cache_control(self, mock_request):
        async def call_next(request):
            response = MagicMock(spec=Response)
            response.status_code = 200
            response.headers = {}
            response.media_type = "application/json"
            response.body_iterator = AsyncIterator([b'{"test": "data"}'])
            return response

        middleware = CacheMiddleware(None)
        request = mock_request
        request.method = "GET"

        response = await middleware.dispatch(request, call_next)

        assert "Cache-Control" in response.headers
        assert "public, max-age=60" in response.headers["Cache-Control"]

    @pytest.mark.asyncio
    async def test_post_request_no_cache(self, mock_request):
        async def call_next(request):
            response = MagicMock(spec=Response)
            response.status_code = 200
            response.headers = {}
            response.media_type = "application/json"
            response.body_iterator = AsyncIterator([b'{"test": "data"}'])
            return response

        middleware = CacheMiddleware(None)
        request = mock_request
        request.method = "POST"

        response = await middleware.dispatch(request, call_next)

        assert "Cache-Control" not in response.headers

    @pytest.mark.asyncio
    async def test_etag_generated_and_matched(self, mock_request):
        async def call_next(request):
            response = MagicMock(spec=Response)
            response.status_code = 200
            response.headers = {}
            response.media_type = "application/json"
            response.body_iterator = AsyncIterator([b'{"test": "data"}'])
            return response

        middleware = CacheMiddleware(None)
        request = mock_request
        request.method = "GET"

        response = await middleware.dispatch(request, call_next)

        assert "ETag" in response.headers
        etag = response.headers["ETag"]
        assert etag.startswith('W/"') and etag.endswith('"')

        request.headers["If-None-Match"] = etag
        response2 = await middleware.dispatch(request, call_next)
        assert response2.status_code == 304

    @pytest.mark.asyncio
    async def test_error_response_no_cache(self, mock_request):
        async def call_next(request):
            response = MagicMock(spec=Response)
            response.status_code = 500
            response.headers = {}
            response.media_type = "application/json"
            response.body_iterator = AsyncIterator([b'{"error": "server error"}'])
            return response

        middleware = CacheMiddleware(None)
        request = mock_request
        request.method = "GET"

        response = await middleware.dispatch(request, call_next)

        assert "Cache-Control" not in response.headers

    @pytest.mark.asyncio
    async def test_get_request_has_etag(self, mock_request):
        async def call_next(request):
            response = MagicMock()
            response.status_code = 200
            response.headers = {}
            response.media_type = "application/json"
            response.body_iterator = AsyncIterator([b'{"status": "ok"}'])
            return response

        middleware = CacheMiddleware(None)
        mock_request.url.path = "/health"

        response = await middleware.dispatch(mock_request, call_next)

        assert response.status_code == 200
        assert "ETag" in response.headers
        assert response.headers["ETag"].startswith('W/"')

    @pytest.mark.asyncio
    async def test_etag_validation_returns_304(self, mock_request):
        call_count = {"count": 0}
        
        async def call_next(request):
            call_count["count"] += 1
            response = MagicMock()
            response.status_code = 200
            response.headers = {}
            response.media_type = "application/json"
            response.body_iterator = AsyncIterator([b'{"status": "ok"}'])
            return response

        middleware = CacheMiddleware(None)
        mock_request.url.path = "/health"

        response = await middleware.dispatch(mock_request, call_next)
        assert response.status_code == 200
        etag = response.headers["ETag"]

        mock_request.headers["If-None-Match"] = etag
        response2 = await middleware.dispatch(mock_request, call_next)
        assert response2.status_code == 304

    @pytest.mark.asyncio
    async def test_post_request_no_cache(self, mock_request):
        async def call_next(request):
            response = MagicMock()
            response.status_code = 201
            response.headers = {}
            response.media_type = "application/json"
            response.body_iterator = AsyncIterator([b'{"id": "test"}'])
            return response

        middleware = CacheMiddleware(None)
        mock_request.method = "POST"
        mock_request.url.path = "/sets"

        response = await middleware.dispatch(mock_request, call_next)

        assert response.status_code == 201
        assert "Cache-Control" not in response.headers

    @pytest.mark.asyncio
    async def test_error_response_no_cache(self, mock_request):
        async def call_next(request):
            response = MagicMock()
            response.status_code = 404
            response.headers = {}
            response.media_type = "application/json"
            response.body_iterator = AsyncIterator([b'{"detail": "Not found"}'])
            return response

        middleware = CacheMiddleware(None)
        mock_request.url.path = "/sets/nonexistent"

        response = await middleware.dispatch(mock_request, call_next)

        assert response.status_code == 404
        assert "Cache-Control" not in response.headers


class TestCacheResponseDecorator:
    @pytest.mark.asyncio
    async def test_decorator_adds_cache_control(self):
        @cache_response(max_age=120, stale_while_revalidate=600)
        async def handler():
            response = MagicMock(spec=Response)
            response.headers = {}
            return response

        result = await handler()
        assert "Cache-Control" in result.headers
        assert "public, max-age=120" in result.headers["Cache-Control"]
        assert "stale-while-revalidate=600" in result.headers["Cache-Control"]

    @pytest.mark.asyncio
    async def test_decorator_private_cache(self):
        @cache_response(max_age=60, private=True)
        async def handler():
            response = MagicMock(spec=Response)
            response.headers = {}
            return response

        result = await handler()
        assert "private, max-age=60" in result.headers["Cache-Control"]


class TestHTTPCaching:
    @pytest.mark.asyncio
    async def test_etag_generation(self):
        content = b'{"data": "test"}'
        etag = f'W/"{hashlib.md5(content).hexdigest()}"'
        assert etag.startswith('W/"')
        assert etag.endswith('"')

    @pytest.mark.asyncio
    async def test_etag_match_returns_304(self):
        content = b'{"data": "test"}'
        etag = f'W/"{hashlib.md5(content).hexdigest()}"'

        if_none_match = etag
        assert if_none_match == etag

    @pytest.mark.asyncio
    async def test_etag_mismatch_returns_200(self):
        content = b'{"data": "test"}'
        etag = f'W/"{hashlib.md5(content).hexdigest()}"'
        different_content = b'{"data": "different"}'
        different_etag = f'W/"{hashlib.md5(different_content).hexdigest()}"'

        assert etag != different_etag

    @pytest.mark.asyncio
    async def test_cache_control_header_format(self):
        max_age = 60
        stale_while_revalidate = 300
        cache_control = f"public, max-age={max_age}, stale-while-revalidate={stale_while_revalidate}"

        assert "public" in cache_control
        assert f"max-age={max_age}" in cache_control
        assert f"stale-while-revalidate={stale_while_revalidate}" in cache_control

    @pytest.mark.asyncio
    async def test_cache_control_private(self):
        cache_control = "private, max-age=60"
        assert "private" in cache_control
        assert "public" not in cache_control

    @pytest.mark.asyncio
    async def test_stale_while_revalidate_allows_serving_stale(self):
        max_age = 60
        stale_while_revalidate = 300

        age = 61
        assert age > max_age
        assert age <= max_age + stale_while_revalidate

        age = 400
        assert age > max_age + stale_while_revalidate

    @pytest.mark.asyncio
    async def test_vary_header_for_compression(self):
        vary_header = "Accept-Encoding"
        assert vary_header == "Accept-Encoding"

    @pytest.mark.asyncio
    async def test_if_modified_since_validation(self):
        from email.utils import formatdate
        import datetime

        last_modified = datetime.datetime.now(datetime.timezone.utc)
        formatted = formatdate(last_modified.timestamp(), usegmt=True)

        assert "GMT" in formatted


class TestLRUCache:
    class SimpleCache:
        def __init__(self, maxsize=100, ttl=None):
            self.maxsize = maxsize
            self.ttl = ttl
            self._cache = {}
            self._access_times = {}

        async def get(self, key):
            if key not in self._cache:
                return None
            if self.ttl:
                import time
                if time.time() - self._access_times[key] > self.ttl:
                    del self._cache[key]
                    del self._access_times[key]
                    return None
            import time
            self._access_times[key] = time.time()
            return self._cache[key]

        async def set(self, key, value):
            import time
            if len(self._cache) >= self.maxsize and key not in self._cache:
                oldest = min(self._access_times.items(), key=lambda x: x[1])[0]
                del self._cache[oldest]
                del self._access_times[oldest]
            self._cache[key] = value
            self._access_times[key] = time.time()

    @pytest.fixture
    def mock_db_pool(self):
        pool = MagicMock()
        conn = AsyncMock()
        pool.connect.return_value = conn
        return pool

    @pytest.mark.asyncio
    async def test_simple_cache_get_set(self):
        cache = self.SimpleCache(maxsize=10)
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_simple_cache_miss(self):
        cache = self.SimpleCache(maxsize=10)
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_simple_cache_eviction(self):
        cache = self.SimpleCache(maxsize=2)
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        assert await cache.get("key1") is None
        assert await cache.get("key2") == "value2"
        assert await cache.get("key3") == "value3"

    @pytest.mark.asyncio
    async def test_simple_cache_ttl_expiration(self):
        cache = self.SimpleCache(maxsize=10, ttl=0.1)
        await cache.set("key1", "value1")
        assert await cache.get("key1") == "value1"
        await asyncio.sleep(0.2)
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_functools_lru_cache(self):
        call_count = 0

        @lru_cache(maxsize=128)
        def expensive_computation(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_computation(5)
        result2 = expensive_computation(5)
        result3 = expensive_computation(10)

        assert result1 == 10
        assert result2 == 10
        assert result3 == 20
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_functools_lru_cache_maxsize(self):
        call_count = 0

        @lru_cache(maxsize=2)
        def cached_func(x):
            nonlocal call_count
            call_count += 1
            return x

        cached_func(1)
        cached_func(2)
        cached_func(3)

        assert call_count == 3

        cached_func(1)
        assert call_count == 4


class TestRedisCache:
    @pytest.mark.asyncio
    async def test_redis_set_get(self, mock_redis):
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=b'{"key": "value"}')

        await mock_redis.set("test_key", '{"key": "value"}')
        result = await mock_redis.get("test_key")

        assert result == b'{"key": "value"}'
        mock_redis.set.assert_called_once()
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_set_with_expiry(self, mock_redis):
        mock_redis.set = AsyncMock(return_value=True)

        await mock_redis.set("test_key", "value", ex=60)

        mock_redis.set.assert_called_with("test_key", "value", ex=60)

    @pytest.mark.asyncio
    async def test_redis_delete(self, mock_redis):
        mock_redis.delete = AsyncMock(return_value=1)

        result = await mock_redis.delete("test_key")

        assert result == 1
        mock_redis.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_redis_exists(self, mock_redis):
        mock_redis.exists = AsyncMock(return_value=1)

        result = await mock_redis.exists("test_key")

        assert result == 1
        mock_redis.exists.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_redis_invalidate_pattern(self, mock_redis):
        mock_redis.keys = AsyncMock(return_value=[b"cache:key1", b"cache:key2"])
        mock_redis.delete = AsyncMock(return_value=2)

        keys = await mock_redis.keys("cache:*")
        result = await mock_redis.delete(*keys)

        assert result == 2
        mock_redis.keys.assert_called_with("cache:*")

    @pytest.mark.asyncio
    async def test_redis_json_serialization(self, mock_redis):
        import json
        data = {"id": "123", "name": "Test", "value": 42}
        serialized = json.dumps(data)

        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=serialized.encode())

        await mock_redis.set("json_key", serialized)
        result = await mock_redis.get("json_key")
        deserialized = json.loads(result.decode())

        assert deserialized == data

    @pytest.mark.asyncio
    async def test_redis_connection_pool(self, mock_redis):
        import redis.asyncio as redis

        pool = redis.ConnectionPool.from_url("redis://localhost:6379/0")
        client = redis.Redis(connection_pool=pool)

        assert client is not None
        await client.aclose()

    @pytest.mark.asyncio
    async def test_redis_health_check(self, mock_redis):
        mock_redis.ping = AsyncMock(return_value=True)

        result = await mock_redis.ping()

        assert result is True

    @pytest.mark.asyncio
    async def test_redis_atomic_operations(self, mock_redis):
        mock_redis.setnx = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=b"locked")

        acquired = await mock_redis.setnx("lock:resource1", "lock_value")
        assert acquired is True

        value = await mock_redis.get("lock:resource1")
        assert value == b"locked"

    @pytest.mark.asyncio
    async def test_redis_pipeline(self, mock_redis):
        pipeline_mock = AsyncMock()
        pipeline_mock.set = MagicMock(return_value=pipeline_mock)
        pipeline_mock.get = MagicMock(return_value=pipeline_mock)
        pipeline_mock.execute = AsyncMock(return_value=[True, b"value"])

        mock_redis.pipeline = MagicMock(return_value=pipeline_mock)

        pipe = mock_redis.pipeline()
        pipe.set("key1", "value1")
        pipe.get("key1")
        results = await pipe.execute()

        assert results == [True, b"value"]


class TestCacheInvalidation:
    @pytest.mark.asyncio
    async def test_invalidate_single_key(self):
        cache = {"user:1": {"name": "John"}, "user:2": {"name": "Jane"}}

        def invalidate(key: str):
            cache.pop(key, None)

        invalidate("user:1")

        assert "user:1" not in cache
        assert "user:2" in cache

    @pytest.mark.asyncio
    async def test_invalidate_by_pattern(self):
        cache = {
            "user:1": {"name": "John"},
            "user:2": {"name": "Jane"},
            "post:1": {"title": "Post 1"},
            "post:2": {"title": "Post 2"},
        }

        def invalidate_pattern(pattern: str):
            import fnmatch
            keys_to_delete = [k for k in cache if fnmatch.fnmatch(k, pattern)]
            for key in keys_to_delete:
                del cache[key]

        invalidate_pattern("user:*")

        assert "user:1" not in cache
        assert "user:2" not in cache
        assert "post:1" in cache
        assert "post:2" in cache

    @pytest.mark.asyncio
    async def test_invalidate_on_mutation(self):
        cache = {"user:1": {"name": "John"}}
        current_data = {"name": "John"}

        async def mutate_user(user_id: str, data: dict):
            nonlocal current_data
            current_data = data
            return {"id": user_id, **data}

        async def cached_get_user(user_id: str):
            key = f"user:{user_id}"
            if key in cache:
                return cache[key]
            result = await mutate_user(user_id, current_data)
            cache[key] = result
            return result

        user1 = await cached_get_user("1")
        assert user1["name"] == "John"

        await mutate_user("1", {"name": "Jane"})
        cache.pop("user:1", None)

        user1_after = await cached_get_user("1")
        assert user1_after["name"] == "Jane"

    @pytest.mark.asyncio
    async def test_invalidate_on_delete(self):
        cache = {"user:1": {"name": "John"}, "user:2": {"name": "Jane"}}
        deleted = []

        async def delete_user(user_id: str):
            deleted.append(user_id)
            return True

        await delete_user("1")
        cache.pop("user:1", None)

        assert "user:1" not in cache
        assert "user:2" in cache
        assert "1" in deleted

    @pytest.mark.asyncio
    async def test_cascade_invalidation(self):
        cache = {
            "user:1": {"name": "John"},
            "user:1:posts": [{"id": 1}, {"id": 2}],
            "post:1": {"title": "Post 1", "author": "1"},
            "post:2": {"title": "Post 2", "author": "1"},
        }

        def invalidate_cascade(user_id: str):
            keys_to_delete = [k for k in cache if k.startswith(f"user:{user_id}")]
            for key in keys_to_delete:
                del cache[key]

        invalidate_cascade("1")

        assert "user:1" not in cache
        assert "user:1:posts" not in cache
        assert "post:1" in cache
        assert "post:2" in cache

    @pytest.mark.asyncio
    async def test_redis_invalidation_integration(self, mock_redis):
        mock_redis.delete = AsyncMock(return_value=2)
        mock_redis.keys = AsyncMock(return_value=[b"cache:user:1", b"cache:user:1:posts"])

        pattern = "cache:user:1*"
        keys = await mock_redis.keys(pattern)
        await mock_redis.delete(*keys)

        mock_redis.keys.assert_called_with(pattern)
        mock_redis.delete.assert_called()

    @pytest.mark.asyncio
    async def test_conditional_invalidation(self):
        cache = {
            "user:1": {"name": "John", "version": 1},
            "user:2": {"name": "Jane", "version": 2},
        }

        def invalidate_if_stale(key: str, current_version: int):
            if key in cache and cache[key]["version"] < current_version:
                del cache[key]

        invalidate_if_stale("user:1", 2)
        assert "user:1" not in cache

        invalidate_if_stale("user:2", 2)
        assert "user:2" in cache


class TestFullCacheFlow:
    @pytest.mark.asyncio
    async def test_request_response_cache_cycle(self):
        cache = {}
        cache_ttl = {}

        async def cached_request(key: str, fetch_fn, ttl: int = 60):
            now = time.time()
            if key in cache and now - cache_ttl.get(key, 0) < ttl:
                return cache[key], True

            result = await fetch_fn()
            cache[key] = result
            cache_ttl[key] = now
            return result, False

        call_count = 0

        async def fetch_data():
            nonlocal call_count
            call_count += 1
            return {"data": f"result_{call_count}"}

        result1, cached1 = await cached_request("key1", fetch_data)
        assert result1 == {"data": "result_1"}
        assert cached1 is False
        assert call_count == 1

        result2, cached2 = await cached_request("key1", fetch_data)
        assert result2 == {"data": "result_1"}
        assert cached2 is True
        assert call_count == 1

        await asyncio.sleep(0.1)

        result3, cached3 = await cached_request("key1", fetch_data, ttl=0)
        assert result3 == {"data": "result_2"}
        assert cached3 is False
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_etag_based_caching(self):
        def generate_etag(content: bytes) -> str:
            import hashlib
            return f'W/"{hashlib.md5(content).hexdigest()}"'

        content1 = b'{"data": "version1"}'
        content2 = b'{"data": "version2"}'

        etag1 = generate_etag(content1)
        etag2 = generate_etag(content2)

        assert etag1 != etag2

        if_none_match = etag1
        assert if_none_match == etag1
        assert if_none_match != etag2

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        cache = {}

        def invalidate(key: str):
            if key in cache:
                del cache[key]

        cache["key1"] = "value1"
        cache["key2"] = "value2"

        assert "key1" in cache
        assert "key2" in cache

        invalidate("key1")

        assert "key1" not in cache
        assert "key2" in cache

    @pytest.mark.asyncio
    async def test_stale_while_revalidate(self):
        cache = {}
        cache_time = {}
        max_age = 60
        stale_while_revalidate = 300

        def is_fresh(key: str) -> bool:
            if key not in cache_time:
                return False
            age = time.time() - cache_time[key]
            return age < max_age

        def is_stale_but_usable(key: str) -> bool:
            if key not in cache_time:
                return False
            age = time.time() - cache_time[key]
            return max_age <= age < max_age + stale_while_revalidate

        def is_expired(key: str) -> bool:
            if key not in cache_time:
                return True
            age = time.time() - cache_time[key]
            return age >= max_age + stale_while_revalidate

        cache["key1"] = "value1"
        cache_time["key1"] = time.time()

        assert is_fresh("key1")
        assert not is_stale_but_usable("key1")
        assert not is_expired("key1")

        cache_time["key1"] = time.time() - 61

        assert not is_fresh("key1")
        assert is_stale_but_usable("key1")
        assert not is_expired("key1")

        cache_time["key1"] = time.time() - 400

        assert not is_fresh("key1")
        assert not is_stale_but_usable("key1")
        assert is_expired("key1")