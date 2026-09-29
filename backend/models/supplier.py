from sqlalchemy import Column, String, Float, Integer, JSON, Enum, DateTime, Uuid
import uuid
from datetime import datetime, timezone
from models import Base
import enum


class SupplierStatus(enum.Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    country = Column(String)
    city = Column(String)
    contact_email = Column(String)
    lead_time_days = Column(Integer)
    reliability_score = Column(Float)
    capabilities = Column(JSON)
    status = Column(Enum(SupplierStatus), default=SupplierStatus.active)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
