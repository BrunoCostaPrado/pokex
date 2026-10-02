import asyncio
from datetime import datetime
from pathlib import Path
from typing import NotRequired, Optional, TypedDict

import httpx
from sqlalchemy import select

from scraper_app.config import settings
from scraper_app.database import get_db
from scraper_app.models import Card, Price, Set

# Expose settings for backward compatibility with tests
settings = settings


class JustTCGSet(TypedDict):
    id: str
    name: str
    series: NotRequired[str]
    total_cards: NotRequired[int]
    release_date: NotRequired[str]
    logo_url: NotRequired[str]
    symbol_url: NotRequired[str]


class JustTCGCard(TypedDict):
    id: str
    set_id: str
    number: str
    name: str
    rarity: NotRequired[str]
    hp: NotRequired[int]
    types: NotRequired[list[str]]
    subtypes: NotRequired[list[str]]
    supertype: NotRequired[str]
    images: NotRequired[dict]
    tcgplayer_url: NotRequired[str]
    cardmarket_url: NotRequired[str]
    prices: NotRequired[dict]


BASE_URL = "https://api.justtcg.com/v1"


async def _request_with_retry(client: httpx.AsyncClient, method: str, url: str, params: dict, max_retries: int = 10) -> httpx.Response:
    response: httpx.Response | None = None
    for attempt in range(max_retries):
        response = await client.request(method, url, params=params)
        if response.status_code == 429:
            wait_time = min(2 ** attempt, 120)
            print(f"Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(wait_time)
            continue
        response.raise_for_status()
        return response
    if response:
        response.raise_for_status()
    raise httpx.HTTPStatusError("Max retries exceeded", request=httpx.Request(method, url), response=response or httpx.Response(500))


async def get_sets(client: httpx.AsyncClient, api_key: str, game: str, page: int = 1, page_size: int = 100) -> list[JustTCGSet]:
    response = await _request_with_retry(client, "GET", "/sets", params={"page": page, "page_size": page_size, "game": game})
    data = response.json()
    return list(data.get("data", []))


async def get_cards(client: httpx.AsyncClient, api_key: str, game: str, set_id: str, page: int = 1, page_size: int = 100) -> list[JustTCGCard]:
    response = await _request_with_retry(client, "GET", f"/sets/{set_id}/cards", params={"page": page, "page_size": page_size, "game": game})
    data = response.json()
    return list(data.get("data", []))


async def get_all_sets(client: httpx.AsyncClient, api_key: str, game: str = "pokemon") -> list[JustTCGSet]:
    all_sets = []
    page = 1
    while True:
        sets = await get_sets(client, api_key, game, page=page)
        if not sets:
            break
        all_sets.extend(sets)
        page += 1
    return all_sets


async def get_all_cards(client: httpx.AsyncClient, api_key: str, game: str, set_id: str) -> list[JustTCGCard]:
    all_cards = []
    page = 1
    while True:
        cards = await get_cards(client, api_key, game, set_id, page=page)
        if not cards:
            break
        all_cards.extend(cards)
        page += 1
    return all_cards


async def _make_client(api_key: str | None = None, game: str = "pokemon") -> httpx.AsyncClient:
    key = api_key or settings.justtcg_api_key or ""
    return httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"X-API-Key": key} if key else {},
        timeout=30.0,
    )


async def sync_sets(http_client: httpx.AsyncClient | None = None, api_key: str | None = None, game: str = "pokemon") -> int:
    client = http_client or await _make_client(api_key, game)
    try:
        sets = await get_all_sets(client, api_key or settings.justtcg_api_key or "", game)
        if not sets:
            return 0

        async for session in get_db():
            for tcg_set in sets:
                existing = await session.get(Set, tcg_set["id"])
                release_date = None
                if tcg_set.get("release_date"):
                    release_date = datetime.fromisoformat(tcg_set["release_date"].replace("Z", "+00:00"))

                if existing:
                    existing.name = tcg_set["name"]
                    existing.series = tcg_set.get("series")
                    existing.total_cards = tcg_set.get("total_cards")
                    existing.release_date = release_date
                    existing.logo_url = tcg_set.get("logo_url")
                    existing.symbol_url = tcg_set.get("symbol_url")
                else:
                    session.add(Set(
                        id=tcg_set["id"],
                        name=tcg_set["name"],
                        series=tcg_set.get("series"),
                        release_date=release_date,
                        total_cards=tcg_set.get("total_cards"),
                        logo_url=tcg_set.get("logo_url"),
                        symbol_url=tcg_set.get("symbol_url"),
                        created_at=datetime.utcnow(),
                    ))
            await session.commit()

        return len(sets)
    finally:
        if http_client is None:
            await client.aclose()


async def sync_cards(http_client: httpx.AsyncClient | None = None, api_key: str | None = None, game: str = "pokemon") -> int:
    client = http_client or await _make_client(api_key, game)
    try:
        async for session in get_db():
            result = await session.execute(select(Set.id))
            set_ids = result.scalars().all()

        total = 0
        for set_id in set_ids:
            cards = await get_all_cards(client, api_key or settings.justtcg_api_key or "", game, set_id)
            if not cards:
                continue

            async for session in get_db():
                for tcg_card in cards:
                    existing = await session.get(Card, tcg_card["id"])
                    if existing:
                        existing.set_id = tcg_card["set_id"]
                        existing.number = tcg_card["number"]
                        existing.name = tcg_card["name"]
                        existing.rarity = tcg_card.get("rarity")
                        existing.hp = tcg_card.get("hp")
                        existing.types = tcg_card.get("types")
                        existing.subtypes = tcg_card.get("subtypes")
                        existing.supertype = tcg_card.get("supertype")
                        existing.images = tcg_card.get("images")
                        existing.tcgplayer_url = tcg_card.get("tcgplayer_url")
                        existing.cardmarket_url = tcg_card.get("cardmarket_url")
                        existing.prices = tcg_card.get("prices")
                    else:
                        session.add(Card(
                            id=tcg_card["id"],
                            set_id=tcg_card["set_id"],
                            number=tcg_card["number"],
                            name=tcg_card["name"],
                            rarity=tcg_card.get("rarity"),
                            hp=tcg_card.get("hp"),
                            types=tcg_card.get("types"),
                            subtypes=tcg_card.get("subtypes"),
                            supertype=tcg_card.get("supertype"),
                            images=tcg_card.get("images"),
                            tcgplayer_url=tcg_card.get("tcgplayer_url"),
                            cardmarket_url=tcg_card.get("cardmarket_url"),
                            prices=tcg_card.get("prices"),
                            created_at=datetime.utcnow(),
                        ))
                    total += 1
                await session.commit()

        return total
    finally:
        if http_client is None:
            await client.aclose()


async def sync_prices(http_client: httpx.AsyncClient | None = None, api_key: str | None = None, game: str = "pokemon") -> int:
    client = http_client or await _make_client(api_key, game)
    try:
        async for session in get_db():
            result = await session.execute(select(Card.id))
            card_ids = result.scalars().all()

        total = 0
        prices_to_add = []

        for card_id in card_ids:
            async for session in get_db():
                card = await session.get(Card, card_id)
                if card and card.prices:
                    for source, price_data in card.prices.items():
                        if isinstance(price_data, dict) and "market" in price_data:
                            prices_to_add.append(Price(
                                card_id=card_id,
                                source=source,
                                price=float(price_data["market"]),
                                currency="USD",
                                updated_at=datetime.utcnow(),
                            ))

        if prices_to_add:
            async for session in get_db():
                session.add_all(prices_to_add)
                await session.commit()
                total = len(prices_to_add)

        return total
    finally:
        if http_client is None:
            await client.aclose()


async def sync_all(http_client: httpx.AsyncClient | None = None, api_key: str | None = None, game: str = "pokemon") -> dict:
    client = http_client or await _make_client(api_key, game)
    try:
        sets_count = await sync_sets(client, api_key, game)
        cards_count = await sync_cards(client, api_key, game)
        prices_count = await sync_prices(client, api_key, game)
        return {
            "sets": sets_count,
            "cards": cards_count,
            "prices": prices_count,
        }
    finally:
        if http_client is None:
            await client.aclose()


async def scrape_limitless_card_images(card_ids: list[str], out_root: Path) -> dict[str, Optional[Path]]:
    """Scrape card images from Limitless TCG for training data.
    
    Args:
        card_ids: List of Limitless card IDs (e.g., ["pt", "sv01-123"])
        out_root: Root directory for saved images
    Returns:
        Dict mapping card_id -> saved path (or None if failed)
    """
    from scraper_app.sources.limitless import scrape_cards_batch
    return await scrape_cards_batch(card_ids, out_root)
