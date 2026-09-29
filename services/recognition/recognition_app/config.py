from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://pokeuser:pokepass@localhost:5432/pokedb"
    detector_type: str = "edge_template"
    template_dir: str | None = None
    cloud_vision_api_key: str | None = None
    cloud_vision_provider: str = "google"
    min_card_area: int = 5000
    max_card_area: int = 500000
    canny_low: int = 50
    canny_high: int = 150

    class Config:
        env_file = ".env"
        env_prefix = ""
        extra = "ignore"


settings = Settings()
