import uuid
from decimal import Decimal
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.database import Base


class Card(Base):
    __tablename__ = "cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    set_name = Column(String, nullable=False)
    card_number = Column(String)
    snkrdunk_id = Column(String, unique=True)
    pricecharting_id = Column(String, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    snapshots = relationship("PriceSnapshot", back_populates="card", order_by="PriceSnapshot.scraped_at")
    watchlist_entry = relationship("WatchlistItem", back_populates="card", uselist=False)


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id = Column(UUID(as_uuid=True), ForeignKey("cards.id"), nullable=False)
    snkrdunk_price_hkd = Column(Numeric(12, 2))
    pricecharting_price_usd = Column(Numeric(12, 2))
    pricecharting_price_hkd = Column(Numeric(12, 2))
    usd_to_hkd_rate = Column(Numeric(10, 4))
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())

    card = relationship("Card", back_populates="snapshots")


class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id = Column(UUID(as_uuid=True), ForeignKey("cards.id"), nullable=False, unique=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    card = relationship("Card", back_populates="watchlist_entry")
