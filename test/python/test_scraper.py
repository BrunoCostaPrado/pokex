import pytest
import httpx
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import asyncio


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_httpx_client():
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    return session


@pytest.fixture
def mock_get_db(mock_db_session):
    async def _gen():
        yield mock_db_session
    return _gen


# ============================================================================
# SCRAPER CLIENT TESTS
# ============================================================================

class TestRequestWithRetry:
    @pytest.mark.asyncio
    async def test_success_on_first_try(self, mock_httpx_client):
        from scraper_app.sync import _request_with_retry
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.request = AsyncMock(return_value=mock_response)

        response = await _request_with_retry(mock_httpx_client, "GET", "/test", {})

        assert response == mock_response
        assert mock_httpx_client.request.call_count == 1

    @pytest.mark.asyncio
    async def test_rate_limited_then_success(self, mock_httpx_client):
        from scraper_app.sync import _request_with_retry
        mock_429 = MagicMock(spec=httpx.Response)
        mock_429.status_code = 429
        mock_200 = MagicMock(spec=httpx.Response)
        mock_200.status_code = 200
        mock_200.raise_for_status = MagicMock()
        mock_httpx_client.request = AsyncMock(side_effect=[mock_429, mock_200])

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            response = await _request_with_retry(mock_httpx_client, "GET", "/test", {})

        assert response == mock_200
        assert mock_httpx_client.request.call_count == 2
        mock_sleep.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, mock_httpx_client):
        from scraper_app.sync import _request_with_retry
        mock_429 = MagicMock(spec=httpx.Response)
        mock_429.status_code = 429
        mock_httpx_client.request = AsyncMock(return_value=mock_429)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(httpx.HTTPStatusError):
                await _request_with_retry(mock_httpx_client, "GET", "/test", {}, max_retries=3)

        assert mock_httpx_client.request.call_count == 3

    @pytest.mark.asyncio
    async def test_network_error_raises(self, mock_httpx_client):
        from scraper_app.sync import _request_with_retry
        mock_httpx_client.request = AsyncMock(side_effect=httpx.NetworkError("Connection failed"))

        with pytest.raises(httpx.NetworkError):
            await _request_with_retry(mock_httpx_client, "GET", "/test", {}, max_retries=1)


class TestMakeClient:
    @pytest.mark.asyncio
    async def test_creates_client_with_api_key(self):
        from scraper_app.sync import _make_client
        with patch("scraper_app.sync.settings") as mock_settings:
            mock_settings.justtcg_api_key = "test-key"
            client = await _make_client()

        assert isinstance(client, httpx.AsyncClient)
        assert str(client.base_url).rstrip("/") == "https://api.justtcg.com/v1"
        assert client.headers.get("X-API-Key") == "test-key"
        await client.aclose()

    @pytest.mark.asyncio
    async def test_creates_client_without_api_key(self):
        from scraper_app.sync import _make_client
        with patch("scraper_app.sync.settings") as mock_settings:
            mock_settings.justtcg_api_key = ""
            client = await _make_client()

        assert isinstance(client, httpx.AsyncClient)
        assert "X-API-Key" not in client.headers
        await client.aclose()


class TestGetSets:
    @pytest.mark.asyncio
    async def test_get_sets_returns_data(self, mock_httpx_client):
        from scraper_app.sync import get_sets
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "set1", "name": "Base Set"}]}
        mock_httpx_client.request = AsyncMock(return_value=mock_response)

        sets = await get_sets(mock_httpx_client, "key", "pokemon")

        assert len(sets) == 1
        assert sets[0]["id"] == "set1"

    @pytest.mark.asyncio
    async def test_get_sets_empty_data(self, mock_httpx_client):
        from scraper_app.sync import get_sets
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_httpx_client.request = AsyncMock(return_value=mock_response)

        sets = await get_sets(mock_httpx_client, "key", "pokemon")

        assert sets == []


class TestGetCards:
    @pytest.mark.asyncio
    async def test_get_cards_returns_data(self, mock_httpx_client):
        from scraper_app.sync import get_cards
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "card1", "name": "Pikachu"}]}
        mock_httpx_client.request = AsyncMock(return_value=mock_response)

        cards = await get_cards(mock_httpx_client, "key", "pokemon", "set1")

        assert len(cards) == 1
        assert cards[0]["id"] == "card1"


class TestGetAllSets:
    @pytest.mark.asyncio
    async def test_get_all_sets_paginates(self, mock_httpx_client):
        from scraper_app.sync import get_all_sets
        call_count = {"count": 0}

        async def mock_get_sets(client, api_key, game, page=1, page_size=100):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return [{"id": f"set{i}"} for i in range(1, 101)]
            return []

        with patch("scraper_app.sync.get_sets", side_effect=mock_get_sets):
            sets = await get_all_sets(mock_httpx_client, "key")

        assert len(sets) == 100
        assert call_count["count"] == 2


class TestGetAllCards:
    @pytest.mark.asyncio
    async def test_get_all_cards_paginates(self, mock_httpx_client):
        from scraper_app.sync import get_all_cards
        call_count = {"count": 0}

        async def mock_get_cards(client, api_key, game, set_id, page=1, page_size=100):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return [{"id": f"card{i}"} for i in range(1, 51)]
            return []

        with patch("scraper_app.sync.get_cards", side_effect=mock_get_cards):
            cards = await get_all_cards(mock_httpx_client, "key", "pokemon", "set1")

        assert len(cards) == 50
        assert call_count["count"] == 2


# ============================================================================
# SCRAPER SYNC TESTS
# ============================================================================

@pytest.fixture(autouse=True)
def patch_sync_settings():
    """Patch sync module settings."""
    with patch("scraper_app.sync.settings") as mock_settings:
        mock_settings.justtcg_api_key = "test-key"
        yield mock_settings


class TestSyncSets:
    @pytest.mark.asyncio
    async def test_sync_sets_inserts_new(self, mock_httpx_client, mock_get_db):
        from scraper_app.sync import sync_sets
        mock_sets = [
            {"id": "set1", "name": "Base Set", "series": "Base", "total_cards": 102,
             "release_date": "1999-01-09T00:00:00Z", "logo_url": "logo.png", "symbol_url": "symbol.png"}
        ]

        mock_session = await mock_get_db().__anext__()
        mock_session.get.return_value = None

        with patch("scraper_app.sync.get_all_sets", return_value=mock_sets):
            with patch("scraper_app.sync.get_db", mock_get_db):
                count = await sync_sets(mock_httpx_client, "test-key")

        assert count == 1
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_sets_updates_existing(self, mock_httpx_client, mock_get_db):
        from scraper_app.sync import sync_sets, Set
        mock_sets = [
            {"id": "set1", "name": "Updated Name", "series": "Base", "total_cards": 102,
             "release_date": "1999-01-09T00:00:00Z", "logo_url": "logo.png", "symbol_url": "symbol.png"}
        ]

        existing_set = Set(id="set1", name="Old Name", series="Base", total_cards=100)
        mock_session = await mock_get_db().__anext__()
        mock_session.get.return_value = existing_set

        with patch("scraper_app.sync.get_all_sets", return_value=mock_sets):
            with patch("scraper_app.sync.get_db", mock_get_db):
                count = await sync_sets(mock_httpx_client, "test-key")

        assert count == 1
        assert existing_set.name == "Updated Name"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_sets_empty_returns_zero(self, mock_httpx_client, mock_get_db):
        from scraper_app.sync import sync_sets

        with patch("scraper_app.sync.get_all_sets", return_value=[]):
            with patch("scraper_app.sync.get_db", mock_get_db):
                count = await sync_sets(mock_httpx_client, "test-key")

        assert count == 0


class TestSyncCards:
    @pytest.mark.asyncio
    async def test_sync_cards_inserts_new(self, mock_httpx_client, mock_get_db):
        from scraper_app.sync import sync_cards
        mock_cards = [
            {"id": "card1", "set_id": "set1", "number": "1", "name": "Pikachu",
             "rarity": "Common", "hp": 60, "types": ["Electric"], "subtypes": ["Basic"],
             "supertype": "Pokémon", "images": {}, "prices": {}}
        ]

        mock_session = await mock_get_db().__anext__()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["set1"]
        mock_session.execute.return_value = mock_result
        mock_session.get.return_value = None

        with patch("scraper_app.sync.get_all_cards", return_value=mock_cards):
            with patch("scraper_app.sync.get_db", mock_get_db):
                count = await sync_cards(mock_httpx_client, "test-key")

        assert count == 1
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_cards_skips_empty_set(self, mock_httpx_client, mock_get_db):
        from scraper_app.sync import sync_cards

        mock_session = await mock_get_db().__anext__()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["set1"]
        mock_session.execute.return_value = mock_result

        with patch("scraper_app.sync.get_all_cards", return_value=[]):
            with patch("scraper_app.sync.get_db", mock_get_db):
                count = await sync_cards(mock_httpx_client, "test-key")

        assert count == 0


class TestSyncPrices:
    @pytest.mark.asyncio
    async def test_sync_prices_inserts_prices(self, mock_httpx_client, mock_get_db):
        from scraper_app.sync import sync_prices, Card
        with patch("scraper_app.sync.Price") as mock_price_class:
            mock_client = mock_httpx_client

            card_with_prices = MagicMock()
            card_with_prices.id = "card1"
            card_with_prices.prices = {"tcgplayer": {"market": 1.50}}
            mock_session = await mock_get_db().__anext__()
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = ["card1"]
            mock_session.execute.return_value = mock_result
            mock_session.get.return_value = card_with_prices

            with patch("scraper_app.sync.get_db", mock_get_db):
                count = await sync_prices(mock_client, "test-key")

            assert count == 1
            mock_session.add_all.assert_called_once()
            mock_price_class.assert_called_once()
            call_kwargs = mock_price_class.call_args.kwargs
            assert call_kwargs["price"] == 1.50
            assert call_kwargs["currency"] == "USD"
            assert call_kwargs["card_id"] == "card1"
            assert call_kwargs["source"] == "tcgplayer"

    @pytest.mark.asyncio
    async def test_sync_prices_skips_card_without_market(self, mock_httpx_client, mock_get_db):
        from scraper_app.sync import sync_prices, Card
        mock_client = mock_httpx_client

        card_no_market = MagicMock()
        card_no_market.id = "card1"
        card_no_market.prices = {"tcgplayer": {"foo": "bar"}}
        mock_session = await mock_get_db().__anext__()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["card1"]
        mock_session.execute.return_value = mock_result
        mock_session.get.return_value = card_no_market

        with patch("scraper_app.sync.get_db", mock_get_db):
            count = await sync_prices(mock_client, "test-key")

        assert count == 0
        mock_session.add_all.assert_not_called()


class TestSyncAll:
    @pytest.mark.asyncio
    async def test_sync_all_calls_all_syncs(self, mock_httpx_client):
        from scraper_app.sync import sync_all

        with patch("scraper_app.sync.sync_sets", new_callable=AsyncMock, return_value=10) as mock_sets:
            with patch("scraper_app.sync.sync_cards", new_callable=AsyncMock, return_value=100) as mock_cards:
                with patch("scraper_app.sync.sync_prices", new_callable=AsyncMock, return_value=50) as mock_prices:
                    result = await sync_all(mock_httpx_client, "test-key")

        assert result == {"sets": 10, "cards": 100, "prices": 50}
        mock_sets.assert_called_once_with(mock_httpx_client, "test-key", "pokemon")
        mock_cards.assert_called_once_with(mock_httpx_client, "test-key", "pokemon")
        mock_prices.assert_called_once_with(mock_httpx_client, "test-key", "pokemon")

    @pytest.mark.asyncio
    async def test_sync_all_closes_client_when_created(self):
        from scraper_app.sync import sync_all
        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()

        with patch("scraper_app.sync._make_client", new_callable=AsyncMock, return_value=mock_client):
            with patch("scraper_app.sync.sync_sets", new_callable=AsyncMock, return_value=0):
                with patch("scraper_app.sync.sync_cards", new_callable=AsyncMock, return_value=0):
                    with patch("scraper_app.sync.sync_prices", new_callable=AsyncMock, return_value=0):
                        await sync_all(None, "test-key")

        mock_client.aclose.assert_called_once()


# ============================================================================
# SCRAPER SCHEDULER TESTS
# ============================================================================

@pytest.fixture
def scraper_modules():
    """Import scraper modules with patched settings."""
    with patch("scraper_app.main.settings") as mock_settings:
        mock_settings.sync_sets_on_startup = False
        mock_settings.sync_interval_hours = 1
        mock_settings.justtcg_api_key = "test-key"
        from scraper_app.main import run_full_sync, _periodic_sync, lifespan, settings, sync_task, init_db
        yield {
            "run_full_sync": run_full_sync,
            "_periodic_sync": _periodic_sync,
            "lifespan": lifespan,
            "settings": settings,
            "sync_task": sync_task,
            "init_db": init_db,
        }


class TestRunFullSync:
    @pytest.mark.asyncio
    async def test_run_full_sync_calls_sync_all(self, scraper_modules):
        with patch("scraper_app.main.sync_all", new_callable=AsyncMock, return_value={"sets": 5, "cards": 50, "prices": 25}) as mock_sync:
            await scraper_modules["run_full_sync"]()
        mock_sync.assert_called_once()


class TestPeriodicSync:
    @pytest.mark.asyncio
    async def test_periodic_sync_runs_loop(self, scraper_modules):
        mock_run_full_sync = AsyncMock()
        call_count = {"count": 0}

        async def counting_sync():
            call_count["count"] += 1
            if call_count["count"] >= 2:
                raise asyncio.CancelledError

        with patch("scraper_app.main.run_full_sync", side_effect=counting_sync):
            with patch("scraper_app.main.settings") as mock_settings:
                mock_settings.sync_interval_hours = 0.0001
                with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                    try:
                        await scraper_modules["_periodic_sync"]()
                    except asyncio.CancelledError:
                        pass

        assert call_count["count"] == 2
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_periodic_sync_respects_interval(self, scraper_modules):
        sleep_calls = []

        async def mock_sleep(duration):
            sleep_calls.append(duration)
            if len(sleep_calls) >= 2:
                raise asyncio.CancelledError

        with patch("scraper_app.main.run_full_sync", new_callable=AsyncMock):
            with patch("scraper_app.main.settings") as mock_settings:
                mock_settings.sync_interval_hours = 1
                with patch("asyncio.sleep", side_effect=mock_sleep):
                    try:
                        await scraper_modules["_periodic_sync"]()
                    except asyncio.CancelledError:
                        pass

        assert len(sleep_calls) == 2
        assert sleep_calls[0] == 3600
        assert sleep_calls[1] == 3600


class TestLifespan:
    @pytest.mark.asyncio
    async def test_lifespan_initializes_db(self, scraper_modules):
        mock_init_db = AsyncMock()
        mock_sync = AsyncMock()

        with patch("scraper_app.main.init_db", mock_init_db):
            with patch("scraper_app.main.run_full_sync", mock_sync):
                with patch("scraper_app.main.settings") as mock_settings:
                    mock_settings.sync_sets_on_startup = True
                    mock_settings.sync_interval_hours = 0

                    app_mock = MagicMock()
                    async with scraper_modules["lifespan"](app_mock):
                        pass

        mock_init_db.assert_called_once()
        mock_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_skips_startup_sync_when_disabled(self, scraper_modules):
        mock_init_db = AsyncMock()
        mock_sync = AsyncMock()

        with patch("scraper_app.main.init_db", mock_init_db):
            with patch("scraper_app.main.run_full_sync", mock_sync):
                with patch("scraper_app.main.settings") as mock_settings:
                    mock_settings.sync_sets_on_startup = False
                    mock_settings.sync_interval_hours = 0

                    app_mock = MagicMock()
                    async with scraper_modules["lifespan"](app_mock):
                        pass

        mock_init_db.assert_called_once()
        mock_sync.assert_not_called()

    @pytest.mark.asyncio
    async def test_lifespan_starts_periodic_task(self, scraper_modules):
        mock_init_db = AsyncMock()

        with patch("scraper_app.main.init_db", mock_init_db):
            with patch("scraper_app.main.settings") as mock_settings:
                mock_settings.sync_sets_on_startup = False
                mock_settings.sync_interval_hours = 1

                app_mock = MagicMock()
                async with scraper_modules["lifespan"](app_mock):
                    # Check task was created by checking global
                    from scraper_app.main import sync_task
                    assert sync_task is not None
                    assert not sync_task.done()

        # Cleanup
        if sync_task and not sync_task.done():
            sync_task.cancel()
            try:
                await sync_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_lifespan_cancels_task_on_exit(self, scraper_modules):
        mock_init_db = AsyncMock()
        cancel_called = {"value": False}

        # Create an awaitable mock that tracks cancel
        class CancellableMock:
            def __init__(self):
                self._cancelled = False
            def cancel(self):
                cancel_called["value"] = True
                self._cancelled = True
            def __await__(self):
                async def coro():
                    if self._cancelled:
                        raise asyncio.CancelledError
                    await asyncio.sleep(0)
                return coro().__await__()

        mock_task = CancellableMock()

        with patch("scraper_app.main.init_db", mock_init_db):
            with patch("scraper_app.main.settings") as mock_settings:
                mock_settings.sync_sets_on_startup = False
                mock_settings.sync_interval_hours = 1
                with patch("asyncio.create_task", return_value=mock_task):
                    app_mock = MagicMock()
                    async with scraper_modules["lifespan"](app_mock):
                        pass

        assert cancel_called["value"]


class TestAppCreation:
    def test_app_created_with_correct_config(self):
        with patch("scraper_app.main.settings") as mock_settings:
            mock_settings.sync_sets_on_startup = False
            mock_settings.sync_interval_hours = 0
            from scraper_app.main import app
            assert app.title == "Scraper Service"
            assert app.description == "Pokemon TCG Data Scraper"
            assert app.version == "0.1.0"