from sqlalchemy import Column, String, Float, ForeignKey, DateTime, Uuid
import uuid
from datetime import datetime, timezone
from models import Base
from sqlalchemy.orm import relationship


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    sku = Column(String, unique=True, nullable=False)
    category = Column(String)
    current_quantity = Column(Float)
    unit = Column(String)
    daily_demand_rate = Column(Float)
    safety_stock = Column(Float)
    reorder_point = Column(Float)
    primary_supplier_id = Column(Uuid, ForeignKey("suppliers.id"))
    unit_cost = Column(Float)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    supplier = relationship("Supplier")
