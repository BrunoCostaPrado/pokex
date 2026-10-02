#!/usr/bin/env python
"""Standalone script to scrape Limitless TCG card images for training."""
import asyncio
import sys
from pathlib import Path

# Add scraper_app to path
sys.path.insert(0, str(Path(__file__).parent))

from scraper_app.sync import scrape_limitless_card_images


async def main():
    # Example card IDs - replace with your list
    card_ids = [
        "pt",  # Example from user
        # Add more card IDs here
    ]

    out_root = Path("data/training/limitless")

    print(f"Scraping {len(card_ids)} cards from Limitless TCG...")
    results = await scrape_limitless_card_images(card_ids, out_root)

    success = sum(1 for p in results.values() if p is not None)
    failed = len(results) - success

    print(f"\nDone: {success} succeeded, {failed} failed")
    for card_id, path in results.items():
        status = "OK" if path else "FAILED"
        print(f"  {card_id}: {status} -> {path}")


if __name__ == "__main__":
    asyncio.run(main())
