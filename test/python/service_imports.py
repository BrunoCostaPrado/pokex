"""Helper to import service modules avoiding namespace conflicts."""
import importlib.util
import sys
from pathlib import Path

# Base path
BASE = Path(__file__).parent.parent.parent / "services"

# Cache for loaded modules
_module_cache = {}


def load_module(service: str, module_path: str):
    """Load a module from a service's app directory."""
    key = f"{service}.{module_path}"
    if key in _module_cache:
        return _module_cache[key]

    # Build the file path
    file_path = BASE / service / "app" / f"{module_path}.py"
    if not file_path.exists():
        # Try with __init__.py for packages
        file_path = BASE / service / "app" / module_path / "__init__.py"
        if not file_path.exists():
            raise ImportError(f"Module {module_path} not found in {service}")

    # Load the module
    spec = importlib.util.spec_from_file_location(key, file_path)
    module = importlib.util.module_from_spec(spec)
    _module_cache[key] = module
    spec.loader.exec_module(module)
    return module


def load_recognition(module_path: str):
    """Load a module from recognition service."""
    return load_module("recognition", module_path)


def load_scraper(module_path: str):
    """Load a module from scraper service."""
    return load_module("scraper", module_path)


def load_data_ingestion(module_path: str):
    """Load a module from data-ingestion service."""
    return load_module("data-ingestion", module_path)