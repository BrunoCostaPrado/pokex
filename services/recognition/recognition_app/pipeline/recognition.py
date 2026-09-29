import io
import numpy as np
from PIL import Image
from typing_extensions import TypedDict

from recognition_app.detector.detector import CardDetector, get_detector, CardDetection

_detector: CardDetector | None = None


def _get_detector() -> CardDetector:
    global _detector
    if _detector is None:
        _detector = get_detector()
    return _detector


class Detection(TypedDict):
    bbox: tuple[float, float, float, float]
    confidence: float
    class_id: int


class RecognitionResult(TypedDict):
    bbox: tuple[float, float, float, float]
    detection_confidence: float
    class_id: int
    ocr_text: str | None


def detect_cards(image: Image.Image) -> list[Detection]:
    img_array = np.array(image)
    detector = _get_detector()
    detections = detector.detect(img_array)
    return [
        Detection(
            bbox=d.bbox,
            confidence=d.confidence,
            class_id=d.class_id,
        )
        for d in detections
    ]


def recognize(image_bytes: bytes) -> list[RecognitionResult]:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    detections = detect_cards(image)
    results: list[RecognitionResult] = []

    for det in detections:
        x1, y1, x2, y2 = map(int, det["bbox"])
        cropped = image.crop((x1, y1, x2, y2))

        ocr_text: str | None = None
        try:
            import pytesseract
            ocr_text = pytesseract.image_to_string(cropped).strip() or None
        except Exception:
            pass

        results.append({
            "bbox": det["bbox"],
            "detection_confidence": det["confidence"],
            "class_id": det["class_id"],
            "ocr_text": ocr_text,
        })

    return results