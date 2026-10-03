# Test configuration for pytest
import sys
from pathlib import Path

# Add service parent directories to sys.path (recognition first for priority)
for svc in ["recognition", "data-ingestion", "scraper"]:
    svc_path = Path(__file__).parent.parent.parent / "services" / svc
    sys.path.insert(0, str(svc_path))

# pytest-asyncio config
pytest_plugins = ["pytest_asyncio"]