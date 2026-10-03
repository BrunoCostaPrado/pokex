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

    # NVIDIA GPU / ONNX Runtime settings
    onnx_model_path: str | None = None
    onnx_device: str = "cuda"  # "cuda" or "cpu"
    onnx_confidence_threshold: float = 0.5
    onnx_iou_threshold: float = 0.45

    # NVIDIA NIM settings
    nim_endpoint: str = "https://integrate.api.nvidia.com/v1"
    nim_model_name: str = "yolo_v8"
    nim_api_key: str | None = None

    class Config:
        env_file = ".env"
        env_prefix = ""
        extra = "ignore"


settings = Settings()
