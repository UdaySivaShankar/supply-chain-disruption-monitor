from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Enum, Uuid
import uuid
from datetime import datetime, timezone
from models import Base
import enum
from sqlalchemy.orm import relationship


class POStatus(enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    in_transit = "in_transit"
    delayed = "delayed"
    delivered = "delivered"
    cancelled = "cancelled"


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    order_number = Column(String, unique=True, nullable=False)
    supplier_id = Column(Uuid, ForeignKey("suppliers.id"))
    inventory_item_id = Column(Uuid, ForeignKey("inventory_items.id"))
    quantity = Column(Float)
    unit_cost = Column(Float)
    total_cost = Column(Float)
    status = Column(Enum(POStatus), default=POStatus.pending)
    order_date = Column(DateTime(timezone=True))
    expected_delivery_date = Column(DateTime(timezone=True))
    actual_delivery_date = Column(DateTime(timezone=True), nullable=True)
    delay_days = Column(Integer, nullable=True)
    notes = Column(String)

    supplier = relationship("Supplier")
    inventory_item = relationship("InventoryItem")
