from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Enum, JSON, Uuid
import uuid
from datetime import datetime, timezone
from models import Base
import enum
from sqlalchemy.orm import relationship


class DisruptionType(enum.Enum):
    supplier_delay = "supplier_delay"
    logistics = "logistics"
    inventory_shortage = "inventory_shortage"
    weather = "weather"
    other = "other"


class Severity(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class DisruptionStatus(enum.Enum):
    detecting = "detecting"
    analyzing = "analyzing"
    recommending = "recommending"
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    resolved = "resolved"


class DisruptionCase(Base):
    __tablename__ = "disruption_cases"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    title = Column(String)
    disruption_type = Column(Enum(DisruptionType))
    severity = Column(Enum(Severity))
    status = Column(Enum(DisruptionStatus), default=DisruptionStatus.detecting)
    affected_supplier_id = Column(Uuid, ForeignKey("suppliers.id"), nullable=True)
    affected_inventory_item_id = Column(Uuid, ForeignKey("inventory_items.id"), nullable=True)
    affected_purchase_order_id = Column(Uuid, ForeignKey("purchase_orders.id"), nullable=True)
    description = Column(String)
    detected_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    delay_days = Column(Integer, default=0)
    inventory_coverage_days = Column(Float, default=0.0)
    stockout_risk = Column(Float, default=0.0)
    estimated_impact_value = Column(Float, default=0.0)
    agent_trace = Column(JSON, default=list)
    recommendation = Column(JSON, default=dict)
    hindsight_memories = Column(JSON, default=list)
    outcome = Column(String, nullable=True)

    affected_supplier = relationship("Supplier")
    affected_inventory_item = relationship("InventoryItem")
    affected_purchase_order = relationship("PurchaseOrder")
