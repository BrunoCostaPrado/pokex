from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://pokeuser:pokepass@localhost:5432/pokedb"
    justtcg_api_key: str = ""
    sync_sets_on_startup: bool = False
    sync_interval_hours: int = 0
    limitless_base_url: str = "https://limitlesstcg.com"
    limitless_rate_limit: float = 1.0

    class Config:
        env_file = ".env"
        env_prefix = ""
        extra = "ignore"


settings = Settings()
