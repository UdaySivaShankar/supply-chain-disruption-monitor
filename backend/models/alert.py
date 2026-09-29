from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Enum, Uuid
import uuid
from datetime import datetime, timezone
from models import Base
from models.disruption_case import Severity
from sqlalchemy.orm import relationship


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    disruption_case_id = Column(Uuid, ForeignKey("disruption_cases.id"))
    alert_type = Column(String)
    severity = Column(Enum(Severity))
    title = Column(String)
    message = Column(String)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    disruption_case = relationship("DisruptionCase")
