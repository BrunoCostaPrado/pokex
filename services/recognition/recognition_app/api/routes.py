from typing import TypedDict

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from recognition_app.pipeline.recognition import RecognitionResult, recognize

router = APIRouter()


class RecognitionResponse(TypedDict):
    detections: list[RecognitionResult]
    count: int


class HealthResponse(TypedDict):
    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return {"status": "ok", "service": "recognition", "version": "0.1.0"}


@router.post("/recognize", response_model=RecognitionResponse)
async def recognize_card(file: UploadFile = File(...)) -> RecognitionResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image",
        )

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image too large (max 10MB)",
        )

    try:
        detections = recognize(image_bytes)
        return {"detections": detections, "count": len(detections)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recognition failed: {str(e)}",
        )
