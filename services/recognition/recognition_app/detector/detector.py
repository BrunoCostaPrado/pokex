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


class ONNXDetector:
    """NVIDIA GPU-accelerated detector using ONNX Runtime with CUDA Execution Provider."""

    def __init__(
        self,
        model_path: str | None = None,
        device: str = "cuda",
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
    ):
        from recognition_app.config import settings
        self.model_path = model_path or getattr(settings, "onnx_model_path", None)
        self.device = device or getattr(settings, "onnx_device", "cuda")
        self.confidence_threshold = confidence_threshold or getattr(settings, "onnx_confidence_threshold", 0.5)
        self.iou_threshold = iou_threshold or getattr(settings, "onnx_iou_threshold", 0.45)
        self._session = None
        self._input_name = None
        self._output_names = None
        self._class_names = None

        if self.model_path:
            self._load_model()

    def _load_model(self) -> None:
        try:
            import onnxruntime as ort

            providers = []
            if self.device == "cuda":
                providers.append(("CUDAExecutionProvider", {"device_id": 0}))
            providers.append("CPUExecutionProvider")

            self._session = ort.InferenceSession(self.model_path, providers=providers)
            self._input_name = self._session.get_inputs()[0].name
            self._output_names = [o.name for o in self._session.get_outputs()]

            # Try to get class names from model metadata
            metadata = self._session.get_modelmeta().custom_metadata_map
            if "names" in metadata:
                import json
                self._class_names = json.loads(metadata["names"])
            else:
                self._class_names = {i: f"class_{i}" for i in range(1000)}  # fallback
        except Exception:
            self._session = None

    def _preprocess(self, image: np.ndarray) -> tuple[np.ndarray, float, int, int]:
        """Preprocess image for YOLOv8 ONNX model (letterbox to 640x640)."""
        input_shape = (640, 640)
        h, w = image.shape[:2]
        scale = min(input_shape[0] / h, input_shape[1] / w)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Letterbox
        canvas = np.full((input_shape[0], input_shape[1], 3), 114, dtype=np.uint8)
        top = (input_shape[0] - new_h) // 2
        left = (input_shape[1] - new_w) // 2
        canvas[top:top + new_h, left:left + new_w] = resized

        # Normalize and transpose to CHW
        canvas = canvas.astype(np.float32) / 255.0
        canvas = np.transpose(canvas, (2, 0, 1))
        canvas = np.expand_dims(canvas, axis=0)
        return canvas, scale, top, left

    def _postprocess(self, outputs: list[np.ndarray], scale: float, top: int, left: int, orig_shape: tuple) -> list[CardDetection]:
        """Postprocess YOLOv8 outputs: NMS, confidence filtering, bbox scaling."""
        if not outputs or outputs[0].size == 0:
            return []

        # YOLOv8 output format: (batch, num_boxes, 84) where 84 = 4 (bbox) + 80 (classes)
        preds = outputs[0][0]  # (num_boxes, 84)
        boxes = preds[:, :4]  # cxcywh
        scores = preds[:, 4:]  # class scores

        # Get max class score and class id
        class_ids = np.argmax(scores, axis=1)
        confidences = np.max(scores, axis=1)

        # Filter by confidence
        mask = confidences >= self.confidence_threshold
        boxes = boxes[mask]
        confidences = confidences[mask]
        class_ids = class_ids[mask]

        if len(boxes) == 0:
            return []

        # Convert cxcywh to xyxy
        cx, cy, w, h = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        x1 = cx - w / 2
        y1 = cy - h / 2
        x2 = cx + w / 2
        y2 = cy + h / 2

        # Scale back to original image size
        x1 = (x1 - left) / scale
        y1 = (y1 - top) / scale
        x2 = (x2 - left) / scale
        y2 = (y2 - top) / scale

        # Clip to image bounds
        orig_h, orig_w = orig_shape[:2]
        x1 = np.clip(x1, 0, orig_w)
        y1 = np.clip(y1, 0, orig_h)
        x2 = np.clip(x2, 0, orig_w)
        y2 = np.clip(y2, 0, orig_h)

        # NMS
        indices = cv2.dnn.NMSBoxes(
            np.column_stack([x1, y1, x2 - x1, y2 - y1]).tolist(),
            confidences.tolist(),
            self.confidence_threshold,
            self.iou_threshold,
        )

        detections: list[CardDetection] = []
        if len(indices) > 0:
            for i in indices.flatten():
                detections.append(CardDetection(
                    bbox=(float(x1[i]), float(y1[i]), float(x2[i]), float(y2[i])),
                    confidence=float(confidences[i]),
                    class_id=int(class_ids[i]),
                ))
        return detections

    def detect(self, image: np.ndarray) -> list[CardDetection]:
        if self._session is None:
            return []

        orig_shape = image.shape
        input_tensor, scale, top, left = self._preprocess(image)

        try:
            outputs = self._session.run(self._output_names, {self._input_name: input_tensor})
            return self._postprocess(outputs, scale, top, left, orig_shape)
        except Exception:
            return []


class NIMDetector:
    """NVIDIA NIM (Inference Microservices) detector for cloud-based inference."""

    def __init__(
        self,
        endpoint: str | None = None,
        model_name: str | None = None,
        api_key: str | None = None,
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        response_parser: callable | None = None,
    ):
        from recognition_app.config import settings
        self.endpoint = endpoint or getattr(settings, "nim_endpoint", "https://integrate.api.nvidia.com/v1")
        self.model_name = model_name or getattr(settings, "nim_model_name", "yolo_v8")
        self.api_key = api_key or getattr(settings, "nim_api_key", None)
        self.confidence_threshold = confidence_threshold or getattr(settings, "onnx_confidence_threshold", 0.5)
        self.iou_threshold = iou_threshold or getattr(settings, "onnx_iou_threshold", 0.45)
        self.response_parser = response_parser or self._default_parser
        self._session = None

        if self.api_key:
            self._init_session()

    def _init_session(self) -> None:
        import requests
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    def _preprocess(self, image: np.ndarray) -> str:
        """Encode image to base64 for NIM API."""
        import base64
        _, encoded = cv2.imencode(".jpg", image)
        return base64.b64encode(encoded.tobytes()).decode("utf-8")

    def _default_parser(self, response: dict, orig_shape: tuple) -> list[CardDetection]:
        """Default NIM YOLO response format: {"boxes": [[x1, y1, x2, y2, conf, class_id], ...]}"""
        detections: list[CardDetection] = []
        boxes = response.get("boxes", [])
        if not boxes:
            return []
        
        orig_h, orig_w = orig_shape[:2]
        
        for box in boxes:
            if len(box) >= 6:
                x1, y1, x2, y2, conf, class_id = box[:6]
                if conf < self.confidence_threshold:
                    continue
                
                # Assume normalized coords (NIM standard); convert to absolute
                if x1 <= 1 and y1 <= 1 and x2 <= 1 and y2 <= 1:
                    x1 *= orig_w
                    y1 *= orig_h
                    x2 *= orig_w
                    y2 *= orig_h
                
                x1 = max(0, min(x1, orig_w))
                y1 = max(0, min(y1, orig_h))
                x2 = max(0, min(x2, orig_w))
                y2 = max(0, min(y2, orig_h))
                
                detections.append(CardDetection(
                    bbox=(float(x1), float(y1), float(x2), float(y2)),
                    confidence=float(conf),
                    class_id=int(class_id),
                ))
        return detections

    def detect(self, image: np.ndarray) -> list[CardDetection]:
        if self._session is None:
            return []
        
        orig_shape = image.shape
        image_b64 = self._preprocess(image)
        
        payload = {
            "model": self.model_name,
            "images": [image_b64],
            "confidence_threshold": self.confidence_threshold,
            "iou_threshold": self.iou_threshold,
        }
        
        try:
            response = self._session.post(
                f"{self.endpoint}/detect",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            # Handle batch response (first image)
            if isinstance(result, list) and result:
                result = result[0]
            elif isinstance(result, dict) and "results" in result:
                result = result["results"][0] if result["results"] else {}
            
            return self.response_parser(result, orig_shape)
        except Exception:
            return []


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
    elif detector_type == "onnx":
        return ONNXDetector()
    elif detector_type == "nim":
        return NIMDetector()
    return EdgeTemplateDetector()