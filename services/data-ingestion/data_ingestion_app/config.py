from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://pokeuser:pokepass@localhost:5432/pokedb"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket: str = "pokemon-cards"

    class Config:
        env_file = ".env"
        env_prefix = ""
        extra = "ignore"


settings = Settings()