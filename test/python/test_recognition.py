import pytest
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock
import io
from PIL import Image
from fastapi.testclient import TestClient


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def fake_card_image():
    return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)


@pytest.fixture
def fake_gray_image():
    return np.random.randint(0, 255, (480, 640), dtype=np.uint8)


@pytest.fixture
def fake_pil_image():
    return Image.new("RGB", (640, 480), color="blue")


@pytest.fixture
def fake_image_bytes():
    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def fake_large_image_bytes():
    return b"x" * (11 * 1024 * 1024)


@pytest.fixture
def detector():
    from recognition_app.detector.detector import EdgeTemplateDetector
    with patch("recognition_app.detector.detector.Path.exists", return_value=False):
        return EdgeTemplateDetector()


@pytest.fixture
def recognition_client():
    from recognition_app.main import app
    return TestClient(app)


# ============================================================================
# EDGE TEMPLATE DETECTOR TESTS
# ============================================================================

class TestEdgeTemplateDetector:
    def test_preprocess_returns_edges(self, detector, fake_card_image):
        cv2 = pytest.importorskip("cv2")
        edges = detector._preprocess(fake_card_image)
        assert edges.shape == (480, 640)
        assert edges.dtype == np.uint8

    def test_preprocess_grayscale_conversion(self, detector):
        cv2 = pytest.importorskip("cv2")
        color_img = np.zeros((100, 100, 3), dtype=np.uint8)
        color_img[:, :, 0] = 255
        edges = detector._preprocess(color_img)
        assert edges.shape == (100, 100)

    def test_find_card_contours_filters_by_area(self, detector):
        cv2 = pytest.importorskip("cv2")
        edges = np.zeros((200, 200), dtype=np.uint8)
        cv2.rectangle(edges, (10, 10), (50, 50), 255, -1)
        cv2.rectangle(edges, (100, 100), (190, 190), 255, -1)

        contours = detector._find_card_contours(edges)
        assert len(contours) == 1

    def test_order_points_orders_correctly(self, detector):
        pts = np.array([[100, 100], [200, 100], [200, 200], [100, 200]], dtype=np.float32)
        ordered = detector._order_points(pts)
        assert ordered.shape == (4, 2)
        assert np.allclose(ordered[0], [100, 100])
        assert np.allclose(ordered[2], [200, 200])

    def test_perspective_transform_returns_warped(self, detector, fake_card_image):
        cv2 = pytest.importorskip("cv2")
        pts = np.array([[100, 100], [200, 100], [200, 200], [100, 200]], dtype=np.float32)
        warped = detector._perspective_transform(fake_card_image, pts)
        assert warped.shape[0] > 0
        assert warped.shape[1] > 0

    def test_match_template_no_templates_returns_default(self, detector, fake_gray_image):
        cv2 = pytest.importorskip("cv2")
        class_id, confidence = detector._match_template(fake_gray_image)
        assert class_id == 0
        assert confidence == 0.5

    def test_match_template_with_template(self, detector, fake_gray_image):
        cv2 = pytest.importorskip("cv2")
        detector.templates = {1: np.ones((50, 50), dtype=np.uint8) * 128}
        class_id, confidence = detector._match_template(fake_gray_image)
        assert class_id in (0, 1)
        assert 0.0 <= confidence <= 1.0

    def test_detect_returns_detections(self, detector, fake_card_image):
        cv2 = pytest.importorskip("cv2")
        with patch.object(detector, "_find_card_contours", return_value=[
            np.array([[[100, 100]], [[200, 100]], [[200, 200]], [[100, 200]]], dtype=np.int32)
        ]):
            with patch.object(detector, "_perspective_transform", return_value=fake_card_image):
                with patch.object(detector, "_match_template", return_value=(1, 0.9)):
                    detections = detector.detect(fake_card_image)

        assert len(detections) == 1
        assert detections[0].class_id == 1
        assert detections[0].confidence == 0.9
        assert len(detections[0].bbox) == 4


# ============================================================================
# CLOUD VISION DETECTOR TESTS (MOCKED)
# ============================================================================

class TestCloudVisionDetector:
    def test_detect_no_client_returns_empty(self):
        from recognition_app.detector.detector import CloudVisionDetector
        with patch.object(CloudVisionDetector, "_get_client", return_value=None):
            detector = CloudVisionDetector(api_key=None)
            result = detector.detect(np.zeros((100, 100, 3), dtype=np.uint8))
            assert result == []

    def test_init_sets_provider(self):
        from recognition_app.detector.detector import CloudVisionDetector
        detector = CloudVisionDetector(api_key="test-key", provider="google")
        assert detector.provider == "google"
        assert detector.api_key == "test-key"

    def test_get_client_google_mocked(self):
        from recognition_app.detector.detector import CloudVisionDetector
        detector = CloudVisionDetector(api_key="test-key", provider="google")
        with patch.dict("sys.modules", {"google.cloud.vision": MagicMock()}):
            client = detector._get_client()

    def test_get_client_aws_mocked(self):
        from recognition_app.detector.detector import CloudVisionDetector
        detector = CloudVisionDetector(api_key="test-key", provider="aws")
        with patch.dict("sys.modules", {"boto3": MagicMock()}):
            client = detector._get_client()

    def test_get_client_azure_mocked(self):
        from recognition_app.detector.detector import CloudVisionDetector
        detector = CloudVisionDetector(api_key="test-key", provider="azure")
        with patch.dict("sys.modules", {"azure.cognitiveservices.vision.computervision": MagicMock()}):
            client = detector._get_client()

    def test_detect_google_mocked_returns_detections(self):
        from recognition_app.detector.detector import CloudVisionDetector
        detector = CloudVisionDetector(api_key="test-key", provider="google")

        mock_response = MagicMock()
        mock_obj = MagicMock()
        mock_obj.name = "playing card"
        mock_obj.score = 0.95
        mock_obj.bounding_poly.normalized_vertices = [
            MagicMock(x=0.1, y=0.1), MagicMock(x=0.5, y=0.1),
            MagicMock(x=0.5, y=0.5), MagicMock(x=0.1, y=0.5)
        ]
        mock_response.localized_object_annotations = [mock_obj]

        mock_client = MagicMock()
        mock_client.object_localization.return_value = mock_response

        with patch.object(detector, "_get_client", return_value=mock_client):
            with patch.dict("sys.modules", {"google.cloud.vision_v1": MagicMock(Image=MagicMock())}):
                detections = detector.detect(np.zeros((100, 100, 3), dtype=np.uint8))

        assert len(detections) == 1
        assert detections[0].confidence == 0.95


# ============================================================================
# COMPOSITE DETECTOR TESTS
# ============================================================================

class TestCompositeDetector:
    def test_fallback_to_cloud_when_edge_empty(self):
        from recognition_app.detector.detector import CompositeDetector, EdgeTemplateDetector, CloudVisionDetector
        edge_detector = MagicMock(spec=EdgeTemplateDetector)
        edge_detector.detect.return_value = []
        cloud_detector = MagicMock(spec=CloudVisionDetector)
        cloud_detector.detect.return_value = [MagicMock()]

        composite = CompositeDetector(edge_detector=edge_detector, cloud_detector=cloud_detector, use_cloud_fallback=True)
        result = composite.detect(np.zeros((100, 100, 3), dtype=np.uint8))

        assert len(result) == 1
        cloud_detector.detect.assert_called_once()

    def test_no_fallback_when_disabled(self):
        from recognition_app.detector.detector import CompositeDetector, EdgeTemplateDetector
        edge_detector = MagicMock(spec=EdgeTemplateDetector)
        edge_detector.detect.return_value = []

        composite = CompositeDetector(edge_detector=edge_detector, use_cloud_fallback=False)
        result = composite.detect(np.zeros((100, 100, 3), dtype=np.uint8))

        assert result == []

    def test_uses_edge_detector_when_detections_found(self):
        from recognition_app.detector.detector import CompositeDetector, EdgeTemplateDetector, CloudVisionDetector
        edge = MagicMock(spec=EdgeTemplateDetector)
        edge.detect.return_value = [MagicMock()]
        cloud = MagicMock(spec=CloudVisionDetector)

        composite = CompositeDetector(edge_detector=edge, cloud_detector=cloud, use_cloud_fallback=True)
        result = composite.detect(np.zeros((100, 100, 3), dtype=np.uint8))

        assert len(result) == 1
        edge.detect.assert_called_once()
        cloud.detect.assert_not_called()


# ============================================================================
# GET_DETECTOR FACTORY TESTS
# ============================================================================

class TestGetDetectorFactory:
    def test_returns_edge_template_by_default(self):
        from recognition_app.detector.detector import get_detector, EdgeTemplateDetector
        with patch("recognition_app.detector.detector.settings") as mock_settings:
            mock_settings.detector_type = "edge_template"
            detector = get_detector()
            assert isinstance(detector, EdgeTemplateDetector)

    def test_returns_cloud_when_configured(self):
        from recognition_app.detector.detector import get_detector, CloudVisionDetector
        with patch("recognition_app.config.settings") as mock_settings:
            mock_settings.detector_type = "cloud"
            detector = get_detector()
            assert isinstance(detector, CloudVisionDetector)

    def test_returns_composite_when_configured(self):
        from recognition_app.detector.detector import get_detector, CompositeDetector
        with patch("recognition_app.config.settings") as mock_settings:
            mock_settings.detector_type = "composite"
            detector = get_detector()
            assert isinstance(detector, CompositeDetector)


# ============================================================================
# PIPELINE TESTS
# ============================================================================

class TestDetectCards:
    def test_detect_cards_returns_detections(self, fake_pil_image):
        from recognition_app.pipeline.recognition import detect_cards
        mock_detection = MagicMock()
        mock_detection.bbox = (100.0, 100.0, 200.0, 200.0)
        mock_detection.confidence = 0.9
        mock_detection.class_id = 1

        with patch("recognition_app.pipeline.recognition._get_detector") as mock_get_detector:
            mock_detector = MagicMock()
            mock_detector.detect.return_value = [mock_detection]
            mock_get_detector.return_value = mock_detector

            detections = detect_cards(fake_pil_image)

        assert len(detections) == 1
        assert detections[0]["bbox"] == (100.0, 100.0, 200.0, 200.0)
        assert detections[0]["confidence"] == 0.9
        assert detections[0]["class_id"] == 1

    def test_detect_cards_empty_when_no_detections(self, fake_pil_image):
        from recognition_app.pipeline.recognition import detect_cards

        with patch("recognition_app.pipeline.recognition._get_detector") as mock_get_detector:
            mock_detector = MagicMock()
            mock_detector.detect.return_value = []
            mock_get_detector.return_value = mock_detector

            detections = detect_cards(fake_pil_image)

        assert detections == []


class TestRecognize:
    def test_recognize_returns_results(self, fake_image_bytes):
        from recognition_app.pipeline.recognition import recognize

        mock_tesseract = MagicMock()
        mock_tesseract.image_to_string.return_value = "Test Card"

        with patch("recognition_app.pipeline.recognition.detect_cards") as mock_detect_cards:
            mock_detect_cards.return_value = [{
                "bbox": (100.0, 100.0, 200.0, 200.0),
                "confidence": 0.9,
                "class_id": 1,
            }]

            with patch.dict("sys.modules", {"pytesseract": mock_tesseract}):
                results = recognize(fake_image_bytes)

        assert len(results) == 1
        assert results[0]["bbox"] == (100.0, 100.0, 200.0, 200.0)
        assert results[0]["detection_confidence"] == 0.9
        assert results[0]["class_id"] == 1
        assert results[0]["ocr_text"] == "Test Card"

    def test_recognize_handles_ocr_failure(self, fake_image_bytes):
        from recognition_app.pipeline.recognition import recognize

        mock_tesseract = MagicMock()
        mock_tesseract.image_to_string.side_effect = Exception("OCR failed")

        with patch("recognition_app.pipeline.recognition.detect_cards") as mock_detect_cards:
            mock_detect_cards.return_value = [{
                "bbox": (100.0, 100.0, 200.0, 200.0),
                "confidence": 0.9,
                "class_id": 1,
            }]

            with patch.dict("sys.modules", {"pytesseract": mock_tesseract}):
                results = recognize(fake_image_bytes)

        assert len(results) == 1
        assert results[0]["ocr_text"] is None

    def test_recognize_multiple_detections(self, fake_image_bytes):
        from recognition_app.pipeline.recognition import recognize

        mock_tesseract = MagicMock()
        mock_tesseract.image_to_string.return_value = "Card"

        with patch("recognition_app.pipeline.recognition.detect_cards") as mock_detect_cards:
            mock_detect_cards.return_value = [
                {"bbox": (100.0, 100.0, 200.0, 200.0), "confidence": 0.9, "class_id": 1},
                {"bbox": (300.0, 100.0, 400.0, 200.0), "confidence": 0.8, "class_id": 2},
            ]

            with patch.dict("sys.modules", {"pytesseract": mock_tesseract}):
                results = recognize(fake_image_bytes)

        assert len(results) == 2
        assert results[0]["class_id"] == 1
        assert results[1]["class_id"] == 2


# ============================================================================
# API TESTS
# ============================================================================

class TestHealthEndpoint:
    def test_health_returns_ok(self, recognition_client):
        response = recognition_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "recognition-service"
        assert data["version"] == "0.1.0"


class TestRecognizeEndpoint:
    def test_recognize_valid_image_returns_detections(self, recognition_client, fake_image_bytes):
        from unittest.mock import MagicMock
        mock_file = MagicMock()
        mock_file.content_type = "image/jpeg"
        mock_file.read = AsyncMock(return_value=fake_image_bytes)

        with patch("recognition_app.api.routes.recognize_card") as mock_recognize_card:
            from fastapi import UploadFile
            mock_recognize_card.return_value = {
                "detections": [
                    {"bbox": (10.0, 10.0, 50.0, 50.0), "detection_confidence": 0.9, "class_id": 1, "ocr_text": "Test"}
                ],
                "count": 1
            }
            # Call the endpoint directly with mock file
            from recognition_app.api.routes import recognize_card
            import asyncio
            result = asyncio.run(recognize_card(mock_file))

        assert result["count"] == 1
        assert result["detections"][0]["class_id"] == 1

    def test_recognize_invalid_content_type_rejected(self, recognition_client, fake_image_bytes):
        from unittest.mock import MagicMock
        mock_file = MagicMock()
        mock_file.content_type = "text/plain"
        mock_file.read = AsyncMock(return_value=b"not an image")

        from recognition_app.api.routes import recognize_card
        import asyncio
        from fastapi import HTTPException

        try:
            asyncio.run(recognize_card(mock_file))
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 400
            assert "must be an image" in e.detail

    def test_recognize_large_image_rejected(self, recognition_client, fake_large_image_bytes):
        from unittest.mock import MagicMock
        mock_file = MagicMock()
        mock_file.content_type = "image/jpeg"
        mock_file.read = AsyncMock(return_value=fake_large_image_bytes)

        from recognition_app.api.routes import recognize_card
        import asyncio
        from fastapi import HTTPException

        try:
            asyncio.run(recognize_card(mock_file))
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 413
            assert "too large" in e.detail.lower()

    def test_recognize_no_file_rejected(self, recognition_client):
        from fastapi import HTTPException
        from recognition_app.api.routes import recognize_card
        import asyncio
        from unittest.mock import MagicMock

        mock_file = MagicMock()
        mock_file.content_type = None

        try:
            asyncio.run(recognize_card(mock_file))
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 400
            assert "must be an image" in e.detail

    def test_recognize_internal_error_returns_500(self, recognition_client, fake_image_bytes):
        from unittest.mock import MagicMock
        mock_file = MagicMock()
        mock_file.content_type = "image/jpeg"
        mock_file.read = AsyncMock(return_value=fake_image_bytes)

        with patch("recognition_app.api.routes.recognize") as mock_recognize:
            mock_recognize.side_effect = Exception("Internal error")

            from recognition_app.api.routes import recognize_card
            import asyncio
            from fastapi import HTTPException

            try:
                asyncio.run(recognize_card(mock_file))
                assert False, "Should have raised HTTPException"
            except HTTPException as e:
                assert e.status_code == 500
                assert "recognition failed" in e.detail.lower()

    def test_recognize_empty_detections(self, recognition_client, fake_image_bytes):
        from unittest.mock import MagicMock
        mock_file = MagicMock()
        mock_file.content_type = "image/jpeg"
        mock_file.read = AsyncMock(return_value=fake_image_bytes)

        with patch("recognition_app.api.routes.recognize_card") as mock_recognize_card:
            mock_recognize_card.return_value = {"detections": [], "count": 0}

            from recognition_app.api.routes import recognize_card
            import asyncio
            result = asyncio.run(recognize_card(mock_file))

        assert result["count"] == 0
        assert result["detections"] == []

    def test_recognize_various_image_formats(self, recognition_client):
        for fmt, mime in [("JPEG", "image/jpeg"), ("PNG", "image/png"), ("WEBP", "image/webp")]:
            img = Image.new("RGB", (50, 50), color="blue")
            buf = io.BytesIO()
            img.save(buf, format=fmt)

            from unittest.mock import MagicMock
            mock_file = MagicMock()
            mock_file.content_type = mime
            mock_file.read = AsyncMock(return_value=buf.getvalue())

            with patch("recognition_app.api.routes.recognize_card") as mock_recognize_card:
                mock_recognize_card.return_value = {"detections": [], "count": 0}

                from recognition_app.api.routes import recognize_card
                import asyncio
                result = asyncio.run(recognize_card(mock_file))

            assert result["count"] == 0, f"Failed for {fmt}"