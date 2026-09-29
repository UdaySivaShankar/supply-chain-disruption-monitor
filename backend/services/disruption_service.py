from models import DisruptionCase, Supplier, InventoryItem, PurchaseOrder, Alert, ApprovalRequest
from models.disruption_case import DisruptionStatus, Severity
from models.approval_request import ApprovalStatus
from utils.logger import logger
from database.connection import AsyncSessionLocal
from sqlalchemy.future import select
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone


async def get_disruption_by_id(case_id: UUID) -> Optional[DisruptionCase]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(DisruptionCase).where(DisruptionCase.id == case_id))
        return result.scalars().first()


async def update_disruption_status(
    case_id: str | UUID,
    status: str,
    agent_trace: Optional[List[Any]] = None,
    recommendation: Optional[Dict[str, Any]] = None,
    hindsight_memories: Optional[List[Any]] = None,
    inventory_coverage_days: Optional[float] = None,
    stockout_risk: Optional[float] = None,
    estimated_impact_value: Optional[float] = None,
    alerts: Optional[List[Dict[str, Any]]] = None,
) -> Optional[DisruptionCase]:
    uid = UUID(str(case_id))
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(DisruptionCase).where(DisruptionCase.id == uid))
        case = result.scalars().first()
        if not case:
            logger.warning(f"DisruptionCase {case_id} not found for status update.")
            return None

        # Convert status string to enum
        try:
            case.status = DisruptionStatus(status)
        except ValueError:
            logger.warning(f"Unknown disruption status value: {status}")

        if agent_trace is not None:
            case.agent_trace = agent_trace
        if recommendation is not None:
            case.recommendation = recommendation
        if hindsight_memories is not None:
            case.hindsight_memories = hindsight_memories
        if inventory_coverage_days is not None:
            case.inventory_coverage_days = inventory_coverage_days
        if stockout_risk is not None:
            case.stockout_risk = stockout_risk
        if estimated_impact_value is not None:
            case.estimated_impact_value = estimated_impact_value

        # Create or update pending ApprovalRequest if entering pending_approval
        if status == "pending_approval" and recommendation:
            app_req_res = await db.execute(
                select(ApprovalRequest).where(ApprovalRequest.disruption_case_id == case.id)
            )
            app_req = app_req_res.scalars().first()
            rec_action = (
                recommendation.get("recommended_action")
                or recommendation.get("action")
                or "Mitigation action pending review"
            )
            rec_summary = recommendation.get("rationale") or rec_action
            conf = float(recommendation.get("confidence_score") or recommendation.get("confidence") or 0.8)
            risk = recommendation.get("risk_level") or "Medium"

            if not app_req:
                app_req = ApprovalRequest(
                    disruption_case_id=case.id,
                    recommendation_summary=rec_summary,
                    recommended_action=rec_action,
                    confidence_score=conf,
                    risk_level=risk,
                    status=ApprovalStatus.pending,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(app_req)
            else:
                app_req.recommendation_summary = rec_summary
                app_req.recommended_action = rec_action
                app_req.confidence_score = conf
                app_req.risk_level = risk
                app_req.status = ApprovalStatus.pending

        # Persist any generated alerts
        if alerts:
            for alert_data in alerts:
                sev_val = alert_data.get("severity", "medium").lower()
                try:
                    alert_sev = Severity(sev_val)
                except ValueError:
                    alert_sev = Severity.medium
                new_alert = Alert(
                    disruption_case_id=case.id,
                    alert_type=alert_data.get("alert_type", "disruption_alert"),
                    severity=alert_sev,
                    title=alert_data.get("title", f"Disruption Alert for {case.title}"),
                    message=alert_data.get("message", "Attention required for active disruption."),
                    is_read=False,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(new_alert)

        await db.commit()
        await db.refresh(case)
        return case
