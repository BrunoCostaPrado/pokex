# Test configuration for pytest
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, AsyncMock

# Remove any existing sqlalchemy modules to ensure our mocks are used
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith("sqlalchemy"):
        del sys.modules[mod_name]

# Mock sqlalchemy
sqlalchemy = ModuleType("sqlalchemy")
sqlalchemy.ext = ModuleType("sqlalchemy.ext")
sqlalchemy.ext.asyncio = ModuleType("sqlalchemy.ext.asyncio")
sqlalchemy.orm = ModuleType("sqlalchemy.orm")
sqlalchemy.dialects = ModuleType("sqlalchemy.dialects")
sqlalchemy.dialects.postgresql = ModuleType("sqlalchemy.dialects.postgresql")

class MockType:
    def __init__(self, *args, **kwargs): pass
    def __call__(self, *args, **kwargs): return self
    def __getitem__(self, item): return self

class MockMapped:
    def __class_getitem__(cls, item): return MockType()

sqlalchemy.ext.asyncio.AsyncSession = MagicMock
sqlalchemy.ext.asyncio.async_sessionmaker = MagicMock
sqlalchemy.ext.asyncio.create_async_engine = MagicMock
sqlalchemy.orm.select = MagicMock
sqlalchemy.orm.declarative_base = MagicMock
sqlalchemy.orm.DeclarativeBase = MagicMock
sqlalchemy.orm.mapped_column = lambda *a, **k: None
sqlalchemy.orm.relationship = lambda *a, **k: None
sqlalchemy.select = sqlalchemy.orm.select
sqlalchemy.desc = MagicMock
sqlalchemy.orm.Mapped = MockMapped
sqlalchemy.JSON = MockType
sqlalchemy.DateTime = MockType
sqlalchemy.Float = MockType
sqlalchemy.ForeignKey = MockType
sqlalchemy.Integer = MockType
sqlalchemy.String = MockType
sqlalchemy.Text = MockType
sqlalchemy.dialects.postgresql.ARRAY = MockType

sys.modules["sqlalchemy"] = sqlalchemy
sys.modules["sqlalchemy.ext"] = sqlalchemy.ext
sys.modules["sqlalchemy.ext.asyncio"] = sqlalchemy.ext.asyncio
sys.modules["sqlalchemy.orm"] = sqlalchemy.orm
sys.modules["sqlalchemy.dialects"] = sqlalchemy.dialects
sys.modules["sqlalchemy.dialects.postgresql"] = sqlalchemy.dialects.postgresql

# Mock pydantic
pydantic = ModuleType("pydantic")
pydantic.BaseModel = MagicMock
pydantic.BaseSettings = MagicMock
pydantic.ConfigDict = MagicMock
pydantic.Field = MagicMock
sys.modules["pydantic"] = pydantic
sys.modules["pydantic_settings"] = ModuleType("pydantic_settings")
sys.modules["pydantic_settings"].BaseSettings = MagicMock

# Mock redis
redis = ModuleType("redis")
redis.asyncio = ModuleType("redis.asyncio")
redis.asyncio.ConnectionPool = MagicMock
redis.asyncio.ConnectionPool.from_url = MagicMock
redis.asyncio.Redis = MagicMock(return_value=AsyncMock(aclose=AsyncMock()))
sys.modules["redis"] = redis
sys.modules["redis.asyncio"] = redis.asyncio

# Mock external dependencies not in test env
sys.modules["psycopg"] = ModuleType("psycopg")
sys.modules["asyncpg"] = ModuleType("asyncpg")
sys.modules["boto3"] = ModuleType("boto3")
sys.modules["boto3.client"] = MagicMock
sys.modules["botocore"] = ModuleType("botocore")
sys.modules["botocore.config"] = ModuleType("botocore.config")
sys.modules["botocore.config"].Config = MagicMock

# Mock numpy for recognition
numpy_mod = ModuleType("numpy")
class MockNDArray:
    def __init__(self, shape=(480, 640, 3), dtype="uint8"):
        self.shape = shape
        self.dtype = dtype
    def __getitem__(self, key): return MockNDArray()
    def __setitem__(self, key, value): pass
    def copy(self): return MockNDArray(self.shape, self.dtype)

numpy_mod.ndarray = MockNDArray
numpy_mod.array = lambda *a, **k: MockNDArray()
numpy_mod.zeros = lambda *a, **k: MockNDArray()
numpy_mod.ones = lambda *a, **k: MockNDArray()
numpy_mod.uint8 = "uint8"
numpy_mod.float32 = "float32"
numpy_mod.int32 = "int32"
numpy_mod.dtype = MagicMock
numpy_random = ModuleType("numpy.random")
numpy_random.randint = lambda *a, **k: MockNDArray()
numpy_mod.random = numpy_random
sys.modules["numpy"] = numpy_mod

# Mock opencv
cv2 = ModuleType("cv2")
cv2.imread = lambda *a, **k: MockNDArray()
cv2.imwrite = lambda *a, **k: True
cv2.resize = lambda *a, **k: MockNDArray()
cv2.cvtColor = lambda *a, **k: MockNDArray()
cv2.imencode = lambda *a, **k: (True, MockNDArray())
cv2.rectangle = lambda *a, **k: MockNDArray()
cv2.COLOR_BGR2RGB = 4
cv2.COLOR_BGR2GRAY = 6
sys.modules["cv2"] = cv2

# Mock PIL
PIL = ModuleType("PIL")
PIL.Image = ModuleType("PIL.Image")
class MockPILImage:
    def __init__(self, *a, **k): pass
    def save(self, *a, **k): pass
    def convert(self, *a, **k): return MockPILImage()
PIL.Image.open = lambda *a, **k: MockPILImage()
PIL.Image.fromarray = lambda *a, **k: MockPILImage()
PIL.Image.new = lambda *a, **k: MockPILImage()
PIL.Image.Image = MockPILImage
sys.modules["PIL"] = PIL
sys.modules["PIL.Image"] = PIL.Image

# Mock pytesseract
sys.modules["pytesseract"] = ModuleType("pytesseract")
sys.modules["pytesseract"].image_to_string = MagicMock

# Mock fastapi with TestClient (use starlette's TestClient)
from starlette.testclient import TestClient as RealTestClient
fastapi = ModuleType("fastapi")
fastapi.FastAPI = MagicMock
fastapi.APIRouter = MagicMock
fastapi.Depends = MagicMock
fastapi.HTTPException = Exception
fastapi.Request = MagicMock
fastapi.Response = MagicMock
fastapi.File = MagicMock
fastapi.UploadFile = MagicMock
fastapi.Query = MagicMock
fastapi.status = ModuleType("status")
for code in [200, 201, 204, 400, 404, 413, 422, 500]:
    setattr(fastapi.status, f"HTTP_{code}_OK" if code == 200 else f"HTTP_{code}_BAD_REQUEST" if code == 400 else f"HTTP_{code}_NOT_FOUND" if code == 404 else f"HTTP_{code}_REQUEST_ENTITY_TOO_LARGE" if code == 413 else f"HTTP_{code}_UNPROCESSABLE_ENTITY" if code == 422 else f"HTTP_{code}_INTERNAL_SERVER_ERROR", code)
fastapi.testclient = ModuleType("fastapi.testclient")
fastapi.testclient.TestClient = RealTestClient
sys.modules["fastapi"] = fastapi
sys.modules["fastapi.routing"] = ModuleType("fastapi.routing")
sys.modules["fastapi.testclient"] = fastapi.testclient

# Add service parent directories to sys.path (recognition first for priority)
for svc in ["recognition", "data-ingestion", "scraper"]:
    svc_path = Path(__file__).parent.parent.parent / "services" / svc
    sys.path.insert(0, str(svc_path))