from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Set(Base):
    __tablename__ = "sets"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    series: Mapped[str | None] = mapped_column(String(100), nullable=True)
    release_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    symbol_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    cards: Mapped[list["Card"]] = relationship("Card", back_populates="set")


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    set_id: Mapped[str] = mapped_column(String(50), ForeignKey("sets.id"))
    number: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(200))
    rarity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    types: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    subtypes: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    supertype: Mapped[str | None] = mapped_column(String(50), nullable=True)
    images: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tcgplayer_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cardmarket_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    prices: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    set: Mapped["Set"] = relationship("Set", back_populates="cards")
    price_history: Mapped[list["Price"]] = relationship("Price", back_populates="card")


class Price(Base):
    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[str] = mapped_column(String(100), ForeignKey("cards.id"))
    source: Mapped[str] = mapped_column(String(50))
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    card: Mapped["Card"] = relationship("Card", back_populates="price_history")
