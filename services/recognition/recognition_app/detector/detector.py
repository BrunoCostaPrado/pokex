from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np
from PIL import Image

from recognition_app.config import settings


@dataclass
class CardDetection:
    bbox: tuple[float, float, float, float]
    confidence: float
    class_id: int


class CardDetector(Protocol):
    def detect(self, image: np.ndarray) -> list[CardDetection]: ...


class EdgeTemplateDetector:
    """Lightweight card detector using edge detection + template matching."""

    def __init__(self, template_dir: str | None = None):
        from recognition_app.config import settings
        self.template_dir = Path(template_dir) if template_dir else Path(settings.template_dir) if settings.template_dir else None
        self.templates: dict[int, np.ndarray] = {}
        self._load_templates()

        self.min_area = getattr(settings, "min_card_area", 5000)
        self.max_area = getattr(settings, "max_card_area", 500000)
        self.canny_low = getattr(settings, "canny_low", 50)
        self.canny_high = getattr(settings, "canny_high", 150)
        self.approx_epsilon = 0.02

    def _load_templates(self) -> None:
        if not self.template_dir or not self.template_dir.exists():
            return
        for template_path in self.template_dir.glob("*.png"):
            try:
                template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
                if template is not None:
                    class_id = int(template_path.stem)
                    self.templates[class_id] = template
            except Exception:
                pass

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, self.canny_low, self.canny_high)
        kernel = np.ones((3, 3), np.uint8)
        return cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    def _find_card_contours(self, edges: np.ndarray) -> list[np.ndarray]:
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cards = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_area or area > self.max_area:
                continue
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, self.approx_epsilon * peri, True)
            if len(approx) == 4:
                cards.append(approx)
        return cards

    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        rect = np.zeros((4, 2), dtype=np.float32)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    def _perspective_transform(self, image: np.ndarray, pts: np.ndarray) -> np.ndarray:
        rect = self._order_points(pts.reshape(4, 2))
        (tl, tr, br, bl) = rect
        width_a = np.linalg.norm(br - bl)
        width_b = np.linalg.norm(tr - tl)
        height_a = np.linalg.norm(tr - br)
        height_b = np.linalg.norm(tl - bl)
        max_width = int(max(width_a, width_b))
        max_height = int(max(height_a, height_b))
        dst = np.array([[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]], dtype=np.float32)
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(image, M, (max_width, max_height))

    def _match_template(self, card_image: np.ndarray) -> tuple[int, float]:
        if not self.templates:
            return 0, 0.5
        gray = cv2.cvtColor(card_image, cv2.COLOR_BGR2GRAY) if len(card_image.shape) == 3 else card_image
        best_class = 0
        best_score = 0.0
        for class_id, template in self.templates.items():
            if gray.shape[0] < template.shape[0] or gray.shape[1] < template.shape[1]:
                continue
            res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val > best_score:
                best_score = max_val
                best_class = class_id
        return best_class, min(max(best_score, 0.1), 1.0)

    def detect(self, image: np.ndarray) -> list[CardDetection]:
        edges = self._preprocess(image)
        contours = self._find_card_contours(edges)
        detections: list[CardDetection] = []

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            card_img = self._perspective_transform(image, cnt)
            class_id, confidence = self._match_template(card_img)
            detections.append(CardDetection(
                bbox=(float(x), float(y), float(x + w), float(y + h)),
                confidence=confidence,
                class_id=class_id,
            ))

        return detections


class CloudVisionDetector:
    """Cloud vision API detector (placeholder for Google Vision / AWS Rekognition / Azure)."""

    def __init__(self, api_key: str | None = None, provider: str | None = None):
        from recognition_app.config import settings
        self.api_key = api_key or getattr(settings, "cloud_vision_api_key", None)
        self.provider = provider or getattr(settings, "cloud_vision_provider", "google")
        self._client = None

    def _get_client(self):
        if self._client is None and self.api_key:
            if self.provider == "google":
                try:
                    from google.cloud import vision
                    self._client = vision.ImageAnnotatorClient.from_service_account_json(self.api_key)
                except Exception:
                    pass
            elif self.provider == "aws":
                try:
                    import boto3
                    self._client = boto3.client("rekognition", aws_access_key_id=self.api_key)
                except Exception:
                    pass
            elif self.provider == "azure":
                try:
                    from azure.cognitiveservices.vision.computervision import ComputerVisionClient
                    from msrest.authentication import CognitiveServicesCredentials
                    self._client = ComputerVisionClient("", CognitiveServicesCredentials(self.api_key))
                except Exception:
                    pass
        return self._client

    def detect(self, image: np.ndarray) -> list[CardDetection]:
        client = self._get_client()
        if client is None:
            return []

        _, encoded = cv2.imencode(".jpg", image)
        image_bytes = encoded.tobytes()

        detections: list[CardDetection] = []

        try:
            if self.provider == "google":
                from google.cloud.vision_v1 import Image
                vision_image = Image(content=image_bytes)
                response = client.object_localization(image=vision_image)
                for obj in response.localized_object_annotations:
                    if obj.name.lower() in ("playing card", "card", "trading card"):
                        verts = obj.bounding_poly.normalized_vertices
                        h, w = image.shape[:2]
                        x1 = verts[0].x * w
                        y1 = verts[0].y * h
                        x2 = verts[2].x * w
                        y2 = verts[2].y * h
                        detections.append(CardDetection(
                            bbox=(float(x1), float(y1), float(x2), float(y2)),
                            confidence=obj.score,
                            class_id=0,
                        ))

            elif self.provider == "aws":
                response = client.detect_labels(
                    Image={"Bytes": image_bytes},
                    MaxLabels=10,
                    MinConfidence=50
                )
                for label in response["Labels"]:
                    if "card" in label["Name"].lower():
                        for instance in label.get("Instances", []):
                            box = instance["BoundingBox"]
                            h, w = image.shape[:2]
                            x1 = box["Left"] * w
                            y1 = box["Top"] * h
                            x2 = (box["Left"] + box["Width"]) * w
                            y2 = (box["Top"] + box["Height"]) * h
                            detections.append(CardDetection(
                                bbox=(float(x1), float(y1), float(x2), float(y2)),
                                confidence=instance["Confidence"] / 100.0,
                                class_id=0,
                            ))

            elif self.provider == "azure":
                from io import BytesIO
                response = client.detect_objects_in_stream(BytesIO(image_bytes))
                for obj in response.objects:
                    if "card" in obj.object_property.lower():
                        r = obj.rectangle
                        detections.append(CardDetection(
                            bbox=(float(r.x), float(r.y), float(r.x + r.w), float(r.y + r.h)),
                            confidence=obj.confidence,
                            class_id=0,
                        ))

        except Exception:
            pass

        return detections


class CompositeDetector:
    """Composite detector: tries edge/template first, falls back to cloud vision."""

    def __init__(
        self,
        edge_detector: EdgeTemplateDetector | None = None,
        cloud_detector: CloudVisionDetector | None = None,
        use_cloud_fallback: bool = True,
    ):
        self.edge_detector = edge_detector or EdgeTemplateDetector()
        self.cloud_detector = cloud_detector or CloudVisionDetector()
        self.use_cloud_fallback = use_cloud_fallback

    def detect(self, image: np.ndarray) -> list[CardDetection]:
        detections = self.edge_detector.detect(image)
        if not detections and self.use_cloud_fallback:
            detections = self.cloud_detector.detect(image)
        return detections


def get_detector() -> CardDetector:
    """Factory function to get configured detector."""
    from recognition_app.config import settings
    detector_type = getattr(settings, "detector_type", "edge_template")
    if detector_type == "cloud":
        return CloudVisionDetector()
    elif detector_type == "composite":
        return CompositeDetector()
    return EdgeTemplateDetector()