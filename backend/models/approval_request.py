from sqlalchemy import Column, String, Float, ForeignKey, DateTime, Enum, Uuid
import uuid
from datetime import datetime, timezone
from models import Base
import enum
from sqlalchemy.orm import relationship


class ApprovalStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    disruption_case_id = Column(Uuid, ForeignKey("disruption_cases.id"), unique=True)
    recommendation_summary = Column(String)
    recommended_action = Column(String)
    alternative_supplier_id = Column(Uuid, ForeignKey("suppliers.id"), nullable=True)
    confidence_score = Column(Float)
    risk_level = Column(String)
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.pending)
    reviewer_notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    decided_at = Column(DateTime(timezone=True), nullable=True)

    disruption_case = relationship("DisruptionCase")
    alternative_supplier = relationship("Supplier")
