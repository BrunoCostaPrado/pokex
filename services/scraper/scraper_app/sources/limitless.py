"""Limitless TCG card image scraper."""
import asyncio
import re
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from scraper_app.config import settings


async def scrape_card_image(card_id: str, out_dir: Path) -> Optional[Path]:
    """Scrape high-res image for a single card from Limitless TCG.
    
    Args:
        card_id: Card identifier (e.g., "pt", "sv01-123")
        out_dir: Output directory for saved images
    Returns:
        Path to saved image or None if failed
    """
    url = f"{settings.limitless_base_url}/cards/{card_id}"
    out_dir.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # Respect rate limit
        await asyncio.sleep(settings.limitless_rate_limit)

        # Fetch card page
        resp = await client.get(url)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # Find card image - try multiple selectors
        img_tag = (
            soup.select_one(".card-image img") or
            soup.select_one("#card-image") or
            soup.select_one(".card img") or
            soup.select_one("img[alt*='card']") or
            soup.select_one("main img")
        )

        if not img_tag or not img_tag.get("src"):
            return None

        img_url = img_tag["src"]
        if img_url.startswith("//"):
            img_url = "https:" + img_url
        elif img_url.startswith("/"):
            img_url = settings.limitless_base_url + img_url

        # Download image
        await asyncio.sleep(settings.limitless_rate_limit)
        img_resp = await client.get(img_url)
        if img_resp.status_code != 200:
            return None

        # Determine extension
        ext = Path(img_url).suffix.split("?")[0]
        if not ext or ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            ext = ".jpg"

        out_path = out_dir / f"{card_id}{ext}"
        out_path.write_bytes(img_resp.content)
        return out_path


async def scrape_cards_batch(card_ids: list[str], out_root: Path) -> dict[str, Optional[Path]]:
    """Scrape multiple cards with rate limiting.
    
    Args:
        card_ids: List of card identifiers
        out_root: Root output directory (creates subdir per card)
    Returns:
        Dict mapping card_id -> saved path (or None if failed)
    """
    results = {}
    for card_id in card_ids:
        out_dir = out_root / card_id
        path = await scrape_card_image(card_id, out_dir)
        results[card_id] = path
    return results


def extract_card_id_from_url(url: str) -> Optional[str]:
    """Extract card ID from Limitless TCG card URL."""
    m = re.search(r"/cards/([^/?#]+)", url)
    return m.group(1) if m else None
