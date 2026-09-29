from datetime import datetime
from io import BytesIO

import boto3
from botocore.config import Config
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from data_ingestion_app.database import get_db
from data_ingestion_app.config import settings
from data_ingestion_app.models import Card, Price, Set

router = APIRouter()

class SetModel(BaseModel):
    id: str | None = Field(None, max_length=50)
    name: str = Field(..., max_length=200)
    series: str | None = Field(None, max_length=100)
    release_date: datetime | None = None
    total_cards: int | None = None
    logo_url: str | None = Field(None, max_length=500)
    symbol_url: str | None = Field(None, max_length=500)

    model_config = ConfigDict(from_attributes=True)

class CardModel(BaseModel):
    id: str | None = Field(None, max_length=100)
    set_id: str | None = Field(None, max_length=50)
    number: str | None = Field(None, max_length=50)
    name: str = Field(..., max_length=200)
    rarity: str | None = Field(None, max_length=50)
    hp: int | None = None
    types: list[str] | None = None
    subtypes: list[str] | None = None
    supertype: str | None = Field(None, max_length=50)
    images: dict | None = None
    tcgplayer_url: str | None = Field(None, max_length=500)
    cardmarket_url: str | None = Field(None, max_length=500)
    prices: dict | None = None

    model_config = ConfigDict(from_attributes=True)

class PriceModel(BaseModel):
    id: int | None = None
    card_id: str = Field(..., max_length=100)
    source: str = Field(..., max_length=50)
    price: float
    currency: str = Field(default="USD", max_length=3)
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class ImageUploadResponse(BaseModel):
    url: str
    object_name: str

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="data-ingestion", version="0.1.0")

# Sets CRUD
@router.post("/sets", response_model=SetModel, status_code=status.HTTP_201_CREATED, tags=["sets"])
async def create_set(data: SetModel, session: AsyncSession = Depends(get_db)) -> SetModel:
    if not data.id:
        raise HTTPException(status_code=400, detail="Set id is required")
    obj = Set(**data.model_dump(exclude_unset=True))
    session.add(obj)
    await session.flush()
    return SetModel.model_validate(obj)  # type: ignore[no-any-return]

@router.get("/sets/{item_id}", response_model=SetModel, tags=["sets"])
async def get_set(item_id: str, session: AsyncSession = Depends(get_db)) -> SetModel:
    result = await session.execute(select(Set).where(Set.id == item_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Set not found")
    return SetModel.model_validate(obj)  # type: ignore[no-any-return]

@router.get("/sets", response_model=list[SetModel], tags=["sets"])
async def list_sets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db),
) -> list[SetModel]:
    query = select(Set).offset(skip).limit(limit)
    result = await session.execute(query)
    return [SetModel.model_validate(obj) for obj in result.scalars().all()]  # type: ignore[no-any-return]

@router.patch("/sets/{item_id}", response_model=SetModel, tags=["sets"])
async def update_set(item_id: str, data: SetModel, session: AsyncSession = Depends(get_db)) -> SetModel:
    result = await session.execute(select(Set).where(Set.id == item_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Set not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    await session.flush()
    return SetModel.model_validate(obj)  # type: ignore[no-any-return]

@router.delete("/sets/{item_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["sets"])
async def delete_set(item_id: str, session: AsyncSession = Depends(get_db)) -> None:
    result = await session.execute(select(Set).where(Set.id == item_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Set not found")
    await session.delete(obj)

# Cards CRUD
@router.post("/cards", response_model=CardModel, status_code=status.HTTP_201_CREATED, tags=["cards"])
async def create_card(data: CardModel, session: AsyncSession = Depends(get_db)) -> CardModel:
    if not data.id or not data.set_id or not data.number:
        raise HTTPException(status_code=400, detail="Card id, set_id, and number are required")
    obj = Card(**data.model_dump(exclude_unset=True))
    session.add(obj)
    await session.flush()
    return CardModel.model_validate(obj)  # type: ignore[no-any-return]

@router.get("/cards/{item_id}", response_model=CardModel, tags=["cards"])
async def get_card(item_id: str, session: AsyncSession = Depends(get_db)) -> CardModel:
    result = await session.execute(select(Card).where(Card.id == item_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Card not found")
    return CardModel.model_validate(obj)  # type: ignore[no-any-return]

@router.get("/cards", response_model=list[CardModel], tags=["cards"])
async def list_cards(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    set_id: str | None = Query(None),
    name: str | None = Query(None),
    rarity: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
) -> list[CardModel]:
    query = select(Card)
    if set_id:
        query = query.where(Card.set_id == set_id)
    if name:
        query = query.where(Card.name.ilike(f"%{name}%"))
    if rarity:
        query = query.where(Card.rarity == rarity)
    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    return [CardModel.model_validate(obj) for obj in result.scalars().all()]  # type: ignore[no-any-return]

@router.patch("/cards/{item_id}", response_model=CardModel, tags=["cards"])
async def update_card(item_id: str, data: CardModel, session: AsyncSession = Depends(get_db)) -> CardModel:
    result = await session.execute(select(Card).where(Card.id == item_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Card not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    await session.flush()
    return CardModel.model_validate(obj)  # type: ignore[no-any-return]

@router.delete("/cards/{item_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["cards"])
async def delete_card(item_id: str, session: AsyncSession = Depends(get_db)) -> None:
    result = await session.execute(select(Card).where(Card.id == item_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Card not found")
    await session.delete(obj)

# Prices (merged: latest is just limit=1)
@router.post("/prices", response_model=PriceModel, status_code=status.HTTP_201_CREATED)
async def create_price(data: PriceModel, session: AsyncSession = Depends(get_db)) -> PriceModel:
    price = Price(**data.model_dump(exclude_unset=True))
    session.add(price)
    await session.flush()
    return PriceModel.model_validate(price)  # type: ignore[no-any-return]

@router.get("/cards/{card_id}/prices", response_model=list[PriceModel])
async def get_price_history(
    card_id: str,
    source: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db),
) -> list[PriceModel]:
    query = select(Price).where(Price.card_id == card_id)
    if source:
        query = query.where(Price.source == source)
    query = query.order_by(desc(Price.updated_at)).limit(limit)
    result = await session.execute(query)
    return [PriceModel.model_validate(obj) for obj in result.scalars().all()]  # type: ignore[no-any-return]

@router.post("/images/upload", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
) -> ImageUploadResponse:
    client = boto3.client(
        "s3",
        endpoint_url=f"http://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
    bucket = settings.minio_bucket
    content = await file.read()
    object_name = f"cards/{file.filename}"
    client.put_object(
        Bucket=bucket,
        Key=object_name,
        Body=BytesIO(content),
        ContentType=file.content_type or "image/jpeg",
    )
    url = f"http://{settings.minio_endpoint}/{bucket}/{object_name}"
    return ImageUploadResponse(url=url, object_name=object_name)
